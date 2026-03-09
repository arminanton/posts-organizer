from pathlib import Path

from instagram_organizer.config.settings import AppSettings, LoggingSettings
from instagram_organizer.config.validation import validate_settings


def build_settings(tmp_path: Path) -> AppSettings:
    return AppSettings(
        gemini_api_key='secret-key-value',
        gemini_model='gemini-1.5-flash',
        target_account='target',
        base_dir=tmp_path,
        results_root=tmp_path / 'results',
        ig_username='user',
        ig_session_file=tmp_path / 'results' / 'state' / '.ig_session',
        max_ai_images=10,
        logging=LoggingSettings(
            app_log_file=tmp_path / 'results' / 'logs' / 'app.log',
            error_log_file=tmp_path / 'results' / 'logs' / 'error.log',
        ),
    )


def test_settings_redacted_dict_hides_api_key(tmp_path: Path) -> None:
    settings = build_settings(tmp_path)
    payload = settings.to_redacted_dict()
    assert payload['gemini_api_key'].startswith('secr...')
    assert 'secret-key-value' not in str(payload)


def test_validate_settings_reports_missing_session_file_warning(tmp_path: Path) -> None:
    report = validate_settings(build_settings(tmp_path))
    assert report.is_valid is True
    assert any(issue.field_name == 'IG_SESSION_FILE' for issue in report.warnings)
