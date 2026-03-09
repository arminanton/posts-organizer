from __future__ import annotations

import runpy

import pytest

from instagram_organizer.cli.main import main
from instagram_organizer.config.settings import AppSettings, LoggingSettings


def _build_settings(tmp_path):
    return AppSettings(
        gemini_api_key='key',
        gemini_model='gemini-1.5-flash',
        target_account='acct',
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


def test_main_uses_non_strict_settings_for_maintenance_commands(monkeypatch, tmp_path):
    monkeypatch.setattr(
        'instagram_organizer.cli.main.parse_args',
        lambda argv=None: type('Args', (), {'env_file': None, 'command': 'validate-config', 'json': False})(),
    )

    calls: list[bool] = []

    def fake_from_sources(*, env_file=None, overrides=None, strict=True):
        calls.append(strict)
        settings = _build_settings(tmp_path)
        return settings.__class__(
            gemini_api_key='',
            gemini_model=settings.gemini_model,
            target_account='',
            base_dir=settings.base_dir,
            results_root=settings.results_root,
            ig_username=settings.ig_username,
            ig_session_file=settings.ig_session_file,
            max_ai_images=settings.max_ai_images,
            logging=settings.logging,
        )

    monkeypatch.setattr('instagram_organizer.cli.main.AppSettings.from_sources', fake_from_sources)
    monkeypatch.setattr('instagram_organizer.cli.main.configure_logging', lambda logging_settings: None)
    monkeypatch.setattr('instagram_organizer.cli.main.dispatch', lambda args, settings: 0)
    monkeypatch.setattr('instagram_organizer.cli.main.cli_overrides_from_args', lambda args: {})

    assert main([]) == 0
    assert calls == [False]


def test_main_invokes_strict_settings_for_run(monkeypatch, tmp_path):
    monkeypatch.setattr(
        'instagram_organizer.cli.main.parse_args',
        lambda argv=None: type('Args', (), {'env_file': None, 'command': 'run'})(),
    )

    calls: list[bool] = []

    def fake_from_sources(*, env_file=None, overrides=None, strict=True):
        calls.append(strict)
        return _build_settings(tmp_path)

    monkeypatch.setattr('instagram_organizer.cli.main.AppSettings.from_sources', fake_from_sources)
    monkeypatch.setattr('instagram_organizer.cli.main.configure_logging', lambda logging_settings: None)
    monkeypatch.setattr('instagram_organizer.cli.main.dispatch', lambda args, settings: 0)
    monkeypatch.setattr('instagram_organizer.cli.main.cli_overrides_from_args', lambda args: {})

    assert main([]) == 0
    assert calls == [True]


def test_package_module_entrypoint_executes_main(monkeypatch):
    monkeypatch.setattr('instagram_organizer.cli.main.main', lambda argv=None: 0)
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module('instagram_organizer', run_name='__main__')
    assert exc_info.value.code == 0
