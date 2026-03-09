from argparse import Namespace
from pathlib import Path

from instagram_organizer.cli.commands import dispatch
from instagram_organizer.config.settings import AppSettings, LoggingSettings
from instagram_organizer.domain.enums import ProcessingStep
from instagram_organizer.domain.models import RunState
from instagram_organizer.infrastructure.persistence.run_state_repository import RunStateJsonRepository



def build_settings(tmp_path: Path) -> AppSettings:
    return AppSettings(
        gemini_api_key='secret-key-value',
        gemini_model='gemini-1.5-flash',
        target_account='target',
        base_dir=tmp_path,
        results_root=tmp_path / 'results',
        ig_username='sample-user',
        ig_session_file=tmp_path / 'results' / 'state' / '.ig_session',
        max_ai_images=10,
        gemini_inline_max_bytes=18_000_000,
        gemini_use_files_api=True,
        gemini_use_batch_fallback=True,
        logging=LoggingSettings(
            app_log_file=tmp_path / 'results' / 'logs' / 'app.log',
            error_log_file=tmp_path / 'results' / 'logs' / 'error.log',
        ),
    )


class FakeAuthService:
    def __init__(self) -> None:
        self.status_payload = {
            'username': 'sample-user',
            'session_file': '/tmp/.ig_session',
            'exists': True,
            'size_bytes': 123,
            'modified_at_utc': '2026-03-09T00:00:00+00:00',
        }

    def login_with_optional_two_factor(self, username: str | None) -> str:
        return f'logged in as {username}'

    def session_status(self, username: str | None):
        return type('Status', (), {'to_dict': lambda self: dict(FakeAuthService().status_payload), 'username': username, 'session_file': '/tmp/.ig_session', 'exists': True, 'size_bytes': 123, 'modified_at_utc': '2026-03-09T00:00:00+00:00'})()

    def logout(self) -> bool:
        return True


def test_dispatch_show_settings_returns_zero(tmp_path: Path, capsys) -> None:
    code = dispatch(Namespace(command='show-settings'), build_settings(tmp_path))
    out = capsys.readouterr().out
    assert code == 0
    assert 'target_account' in out


def test_dispatch_show_run_state_json_returns_zero(tmp_path: Path, capsys) -> None:
    settings = build_settings(tmp_path)
    RunStateJsonRepository(settings.run_state_file).save(
        RunState(shortcode='abc123', step=ProcessingStep.ANALYZING)
    )
    code = dispatch(Namespace(command='show-run-state', json=True), settings)
    out = capsys.readouterr().out
    assert code == 0
    assert 'abc123' in out


def test_dispatch_login_and_logout_commands(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.setattr('instagram_organizer.cli.commands.build_auth_service', lambda settings: FakeAuthService())
    settings = build_settings(tmp_path)

    login_code = dispatch(Namespace(command='login'), settings)
    logout_code = dispatch(Namespace(command='logout'), settings)
    out = capsys.readouterr().out

    assert login_code == 0
    assert logout_code == 0
    assert 'logged in as sample-user' in out
    assert 'Saved Instagram session removed.' in out


def test_dispatch_session_status_json(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.setattr('instagram_organizer.cli.commands.build_auth_service', lambda settings: FakeAuthService())
    settings = build_settings(tmp_path)

    code = dispatch(Namespace(command='session-status', json=True), settings)
    out = capsys.readouterr().out

    assert code == 0
    assert 'sample-user' in out
    assert 'size_bytes' in out
