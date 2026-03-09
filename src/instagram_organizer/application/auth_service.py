"""Interactive authentication and session lifecycle helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path
from typing import Callable

from instagram_organizer.domain.protocols import InstagramClient, SessionStore


@dataclass(frozen=True, slots=True)
class SessionStatus:
    """Snapshot of the local Instagram session state.

    Args:
        username: Configured Instagram username, if any.
        session_file: Resolved portable session-file path.
        exists: Whether the session file exists on disk.
        size_bytes: Session file size in bytes when available.
        modified_at_utc: ISO timestamp for the last file modification when available.
    """

    username: str | None
    session_file: Path
    exists: bool
    size_bytes: int | None = None
    modified_at_utc: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize the status for JSON CLI output."""

        payload = asdict(self)
        payload['session_file'] = str(self.session_file)
        return payload


@dataclass(slots=True)
class AuthService:
    """Manage interactive Instagram login and local session-file lifecycle."""

    instagram_client: InstagramClient
    session_store: SessionStore
    password_reader: Callable[[str], str] = getpass
    input_reader: Callable[[str], str] = input

    def login(self, username: str | None) -> str:
        """Perform an interactive login and persist the session file.

        Args:
            username: Instagram username to authenticate.

        Returns:
            Human-readable success message.

        Raises:
            ValueError: If no username is available for login.
            Exception: Propagates authentication failures from Instaloader.
        """

        resolved_username = (username or '').strip()
        if not resolved_username:
            raise ValueError('IG_USERNAME is required for the login command.')

        password = self.password_reader(f'Instagram password for {resolved_username}: ')
        self.instagram_client.login(resolved_username, password)

        try:
            self.session_store.save(self.instagram_client.loader)
        except Exception:
            raise
        return f'Instagram session saved for {resolved_username}.'

    def complete_two_factor(self, code: str) -> str:
        """Complete a pending two-factor authentication flow and save the session."""

        self.instagram_client.two_factor_login(code)
        self.session_store.save(self.instagram_client.loader)
        active_user = self.instagram_client.test_login() or 'the configured user'
        return f'Instagram 2FA completed and session saved for {active_user}.'

    def login_with_optional_two_factor(self, username: str | None) -> str:
        """Log in, prompting for a 2FA code when Instaloader requests one."""

        try:
            return self.login(username)
        except Exception as exc:
            if exc.__class__.__name__ != 'TwoFactorAuthRequiredException':
                raise
            code = self.input_reader('Instagram 2FA code: ').strip()
            if not code:
                raise ValueError('A 2FA code is required to complete Instagram login.') from exc
            return self.complete_two_factor(code)

    def session_status(self, username: str | None) -> SessionStatus:
        """Return information about the portable session file."""

        session_path = getattr(self.session_store, 'session_file')
        exists = bool(getattr(self.session_store, 'exists', lambda: session_path.exists())())
        if not exists:
            return SessionStatus(username=(username or None), session_file=session_path, exists=False)

        stat = session_path.stat()
        modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        return SessionStatus(
            username=(username or None),
            session_file=session_path,
            exists=True,
            size_bytes=stat.st_size,
            modified_at_utc=modified,
        )

    def logout(self) -> bool:
        """Remove the saved local session file.

        Returns:
            ``True`` when a session file existed and was removed.
        """

        clearer = getattr(self.session_store, 'clear', None)
        if callable(clearer):
            return bool(clearer())
        session_path = getattr(self.session_store, 'session_file')
        if not session_path.exists():
            return False
        session_path.unlink()
        return True
