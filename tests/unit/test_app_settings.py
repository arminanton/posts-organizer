from pathlib import Path

import pytest

from instagram_organizer.config.settings import AppSettings, LoggingSettings


def test_app_settings_path_properties(tmp_path: Path) -> None:
    settings = AppSettings(
        gemini_api_key='key',
        gemini_model='gemini-1.5-flash',
        target_account='target',
        base_dir=tmp_path,
        results_root=tmp_path / 'results',
        ig_username=None,
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
    assert settings.results_root == tmp_path / 'results'
    assert settings.organized_dir == tmp_path / 'results' / 'library' / 'Organized_Posts'
    assert settings.primary_tracker_file == tmp_path / 'results' / 'state' / 'progress.jsonl'


def test_from_sources_allows_missing_runtime_values_in_non_strict_mode(tmp_path: Path) -> None:
    settings = AppSettings.from_sources(
        overrides={'BASE_DIR': str(tmp_path)},
        strict=False,
    )
    assert settings.base_dir == tmp_path.resolve()
    assert settings.gemini_api_key == ''
    assert settings.target_account == ''
    assert settings.gemini_inline_max_bytes == 18_000_000
    assert settings.gemini_use_files_api is True
    assert settings.gemini_use_batch_fallback is True


def test_from_env_remains_strict_for_runtime_usage(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        AppSettings.from_env(overrides={'BASE_DIR': str(tmp_path)})
