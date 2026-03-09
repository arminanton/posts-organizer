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
        ig_username=None,
        ig_session_file=tmp_path / 'results' / 'state' / '.ig_session',
        max_ai_images=10,
        logging=LoggingSettings(
            app_log_file=tmp_path / 'results' / 'logs' / 'app.log',
            error_log_file=tmp_path / 'results' / 'logs' / 'error.log',
        ),
    )


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
