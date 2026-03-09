from __future__ import annotations

from pathlib import Path

from instagram_organizer.config.settings import AppSettings


def test_from_sources_autoloads_dotenv_from_current_working_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    env_path = tmp_path / '.env'
    env_path.write_text(
        'GEMINI_API_KEY=dotenv-key\n'
        'TARGET_ACCOUNT=dotenv-target\n'
        'IG_USERNAME=dotenv-user\n',
        encoding='utf-8',
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('TARGET_ACCOUNT', raising=False)
    monkeypatch.delenv('IG_USERNAME', raising=False)

    settings = AppSettings.from_sources(strict=True)

    assert settings.gemini_api_key == 'dotenv-key'
    assert settings.target_account == 'dotenv-target'
    assert settings.ig_username == 'dotenv-user'


def test_explicit_env_file_overrides_default_dotenv(tmp_path: Path, monkeypatch) -> None:
    default_env = tmp_path / '.env'
    explicit_env = tmp_path / '.env.alt'
    default_env.write_text(
        'GEMINI_API_KEY=default-key\nTARGET_ACCOUNT=default-target\n',
        encoding='utf-8',
    )
    explicit_env.write_text(
        'GEMINI_API_KEY=explicit-key\nTARGET_ACCOUNT=explicit-target\n',
        encoding='utf-8',
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('TARGET_ACCOUNT', raising=False)

    settings = AppSettings.from_sources(env_file=explicit_env, strict=True)

    assert settings.gemini_api_key == 'explicit-key'
    assert settings.target_account == 'explicit-target'
