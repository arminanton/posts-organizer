from __future__ import annotations

from pathlib import Path

from instagram_organizer.application.auth_service import AuthService
from instagram_organizer.infrastructure.instagram.session_manager import SessionManager


class FakeLoader:
    def save_session_to_file(self, filename: str) -> None:
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        Path(filename).write_text('session', encoding='utf-8')


class FakeInstagramClient:
    def __init__(self) -> None:
        self.loader = FakeLoader()
        self.login_calls: list[tuple[str, str]] = []

    def login(self, username: str, password: str) -> None:
        self.login_calls.append((username, password))

    def two_factor_login(self, code: str) -> None:
        raise AssertionError('2FA not expected in this test')

    def test_login(self) -> str | None:
        return 'sample-user'


def test_auth_service_roundtrip_status_and_logout(tmp_path: Path) -> None:
    session_store = SessionManager(tmp_path / 'results' / 'state' / '.ig_session')
    service = AuthService(
        instagram_client=FakeInstagramClient(),
        session_store=session_store,
        password_reader=lambda prompt: 'password123',
    )

    message = service.login_with_optional_two_factor('sample-user')
    status = service.session_status('sample-user')
    removed = service.logout()

    assert 'sample-user' in message
    assert status.exists is True
    assert removed is True
