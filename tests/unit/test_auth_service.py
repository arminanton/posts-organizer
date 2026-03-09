from __future__ import annotations

from pathlib import Path

from instagram_organizer.application.auth_service import AuthService
from instagram_organizer.infrastructure.instagram.session_manager import SessionManager


class FakeInstagramClient:
    def __init__(self) -> None:
        self.loader = object()
        self.login_calls: list[tuple[str, str]] = []
        self.two_factor_calls: list[str] = []
        self.active_user: str | None = 'sample-user'

    def login(self, username: str, password: str) -> None:
        self.login_calls.append((username, password))

    def two_factor_login(self, code: str) -> None:
        self.two_factor_calls.append(code)

    def test_login(self) -> str | None:
        return self.active_user


class FakeTwoFactorInstagramClient(FakeInstagramClient):
    def login(self, username: str, password: str) -> None:
        super().login(username, password)
        raise type('TwoFactorAuthRequiredException', (Exception,), {})()


class FakeSessionStore(SessionManager):
    def __init__(self, session_file: Path) -> None:
        super().__init__(session_file=session_file)
        self.saved = 0

    def save(self, loader) -> None:
        self.saved += 1
        self.ensure_parent()
        self.session_file.write_text('session', encoding='utf-8')


def test_auth_service_login_saves_session(tmp_path: Path) -> None:
    store = FakeSessionStore(tmp_path / '.ig_session')
    service = AuthService(
        instagram_client=FakeInstagramClient(),
        session_store=store,
        password_reader=lambda prompt: 'password123',
    )

    message = service.login_with_optional_two_factor('armin')

    assert 'armin' in message
    assert store.saved == 1
    assert store.session_file.exists()


def test_auth_service_handles_two_factor(tmp_path: Path) -> None:
    client = FakeTwoFactorInstagramClient()
    store = FakeSessionStore(tmp_path / '.ig_session')
    service = AuthService(
        instagram_client=client,
        session_store=store,
        password_reader=lambda prompt: 'password123',
        input_reader=lambda prompt: '246810',
    )

    message = service.login_with_optional_two_factor('armin')

    assert '2FA completed' in message
    assert client.two_factor_calls == ['246810']
    assert store.saved == 1


def test_auth_service_logout_removes_session_file(tmp_path: Path) -> None:
    store = FakeSessionStore(tmp_path / '.ig_session')
    store.session_file.parent.mkdir(parents=True, exist_ok=True)
    store.session_file.write_text('session', encoding='utf-8')
    service = AuthService(
        instagram_client=FakeInstagramClient(),
        session_store=store,
    )

    removed = service.logout()

    assert removed is True
    assert not store.session_file.exists()
