"""Portable Instaloader session-file management."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SessionManager:
    """Manage portable session-file paths and persistence concerns.

    Args:
        session_file: Portable path used to store the Instagram session snapshot.
    """

    session_file: Path

    def ensure_parent(self) -> None:
        """Create the session-file parent directory if needed."""

        self.session_file.parent.mkdir(parents=True, exist_ok=True)

    def exists(self) -> bool:
        """Return whether the session file currently exists."""

        return self.session_file.exists()

    def load(self, loader: Any, username: str) -> None:
        """Load a session into an Instaloader-like object.

        Args:
            loader: Instaloader-like object with ``load_session_from_file``.
            username: Instagram username associated with the saved session.
        """

        self.ensure_parent()
        loader.load_session_from_file(username, filename=str(self.session_file))

    def save(self, loader: Any) -> None:
        """Persist the current session from an Instaloader-like object."""

        self.ensure_parent()
        loader.save_session_to_file(filename=str(self.session_file))

    def clear(self) -> bool:
        """Delete the session file if present.

        Returns:
            ``True`` when a file was removed, otherwise ``False``.
        """

        if not self.session_file.exists():
            return False
        self.session_file.unlink()
        return True
