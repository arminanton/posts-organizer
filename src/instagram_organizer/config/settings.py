"""Application settings model.

This module centralizes configuration loading and path derivation. The rest of
the application can work with typed values instead of reading raw environment
variables directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dotenv import dotenv_values


def resolve_relative_to_base(base_dir: Path, raw_path: str) -> Path:
    """Resolve a path string relative to ``base_dir`` unless already absolute.

    Args:
        base_dir: Root path used for relative path resolution.
        raw_path: Raw configuration path value.

    Returns:
        A normalized absolute path.
    """

    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (base_dir / candidate).resolve()


@dataclass(frozen=True, slots=True)
class LoggingSettings:
    """Logging configuration values.

    Attributes:
        level: Effective log level name.
        app_log_file: Fully resolved path used for general application logs.
        error_log_file: Fully resolved path used for error-only logs.
    """

    level: str = 'INFO'
    app_log_file: Path = Path('results/logs/app.log')
    error_log_file: Path = Path('results/logs/error.log')


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Top-level application settings.

    Args:
        gemini_api_key: API key used for Gemini access.
        gemini_model: Gemini model name for analysis.
        target_account: Instagram account to inspect.
        base_dir: Project base directory used to resolve runtime paths.
        results_root: Dedicated runtime-results root under ``base_dir``.
        ig_username: Optional Instagram username for session reuse.
        ig_session_file: Portable session file path under ``results_root/state`` by default.
        max_ai_images: Maximum number of images sent to AI per post.
        logging: Nested logging configuration.
    """

    gemini_api_key: str
    gemini_model: str
    target_account: str
    base_dir: Path
    results_root: Path
    ig_username: str | None
    ig_session_file: Path
    max_ai_images: int
    logging: LoggingSettings

    @classmethod
    def from_env(
        cls,
        *,
        env_file: str | Path | None = None,
        overrides: Mapping[str, str] | None = None,
    ) -> 'AppSettings':
        """Load validated settings for runtime commands.

        This strict loader is intended for the main ``run`` workflow and raises
        when required secrets or target identifiers are missing.
        """

        return cls.from_sources(env_file=env_file, overrides=overrides, strict=True)

    @classmethod
    def from_sources(
        cls,
        *,
        env_file: str | Path | None = None,
        overrides: Mapping[str, str] | None = None,
        strict: bool = True,
    ) -> 'AppSettings':
        """Load settings from file, environment, and CLI overrides.

        Precedence is applied in this order:

        1. values from the optional ``env_file``
        2. current ``os.environ`` values
        3. explicit ``overrides`` passed by the CLI

        Args:
            env_file: Optional dotenv file path.
            overrides: Optional mapping of final override values.
            strict: When ``True``, require runtime-critical fields.

        Returns:
            A resolved ``AppSettings`` instance.

        Raises:
            ValueError: When required settings are missing or invalid in strict mode.
        """

        data = cls.merge_sources(env_file=env_file, overrides=overrides)
        gemini_api_key = data.get('GEMINI_API_KEY', '').strip()
        target_account = data.get('TARGET_ACCOUNT', '').strip()
        if strict and (not gemini_api_key or not target_account):
            raise ValueError('GEMINI_API_KEY and TARGET_ACCOUNT are required.')

        base_dir = Path(data.get('BASE_DIR', '.')).expanduser().resolve()
        results_dir_name = data.get('RESULTS_DIR', 'results').strip() or 'results'
        results_root = resolve_relative_to_base(base_dir, results_dir_name)
        session_name = data.get('IG_SESSION_FILE', 'state/.ig_session').strip() or 'state/.ig_session'
        max_ai_images = max(1, int(data.get('MAX_AI_IMAGES', '10')))

        return cls(
            gemini_api_key=gemini_api_key,
            gemini_model=data.get('GEMINI_MODEL', 'gemini-1.5-flash').strip() or 'gemini-1.5-flash',
            target_account=target_account,
            base_dir=base_dir,
            results_root=results_root,
            ig_username=data.get('IG_USERNAME', '').strip() or None,
            ig_session_file=resolve_relative_to_base(results_root, session_name),
            max_ai_images=max_ai_images,
            logging=LoggingSettings(
                level=data.get('LOG_LEVEL', 'INFO').strip().upper(),
                app_log_file=resolve_relative_to_base(
                    results_root,
                    data.get('APP_LOG_FILE', 'logs/app.log').strip() or 'logs/app.log',
                ),
                error_log_file=resolve_relative_to_base(
                    results_root,
                    data.get('ERROR_LOG_FILE', 'logs/error.log').strip() or 'logs/error.log',
                ),
            ),
        )

    @classmethod
    def merge_sources(
        cls,
        *,
        env_file: str | Path | None = None,
        overrides: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        """Merge configuration from file, environment, and overrides.

        Args:
            env_file: Optional dotenv file path.
            overrides: Final-value overrides, usually from CLI flags.

        Returns:
            A merged dictionary of string configuration values.
        """

        merged: dict[str, str] = {}
        if env_file:
            env_path = Path(env_file)
            if env_path.exists():
                merged.update(
                    {
                        key: value
                        for key, value in dotenv_values(env_path).items()
                        if value is not None
                    }
                )
        merged.update(os.environ)
        if overrides:
            merged.update({key: value for key, value in overrides.items() if value is not None})
        return {str(key): str(value) for key, value in merged.items()}

    @classmethod
    def resolve_base_dir(
        cls,
        *,
        env_file: str | Path | None = None,
        overrides: Mapping[str, str] | None = None,
    ) -> Path:
        """Resolve ``BASE_DIR`` without requiring runtime secrets.

        This helper supports maintenance commands that should remain usable even
        when the full scraping configuration is incomplete.
        """

        data = cls.merge_sources(env_file=env_file, overrides=overrides)
        return Path(data.get('BASE_DIR', '.')).expanduser().resolve()

    def to_redacted_dict(self) -> dict[str, object]:
        """Return a safe-to-display dictionary of settings.

        Secrets are redacted so operators can inspect the resolved configuration
        without leaking credentials into logs or terminals.
        """

        api_key = self.gemini_api_key
        if len(api_key) <= 8:
            redacted_key = '*' * len(api_key)
        else:
            redacted_key = f"{api_key[:4]}...{api_key[-4:]}"

        return {
            'gemini_api_key': redacted_key,
            'gemini_model': self.gemini_model,
            'target_account': self.target_account,
            'base_dir': str(self.base_dir),
            'results_root': str(self.results_root),
            'library_dir': str(self.library_dir),
            'state_dir': str(self.state_dir),
            'logs_dir': str(self.logs_dir),
            'ig_username': self.ig_username,
            'ig_session_file': str(self.ig_session_file),
            'max_ai_images': self.max_ai_images,
            'organized_dir': str(self.organized_dir),
            'manual_dir': str(self.manual_dir),
            'duplicates_dir': str(self.duplicates_dir),
            'workspace_dir': str(self.workspace_dir),
            'primary_tracker_file': str(self.primary_tracker_file),
            'duplicate_tracker_file': str(self.duplicate_tracker_file),
            'run_state_file': str(self.run_state_file),
            'primary_index_file': str(self.primary_index_file),
            'duplicate_index_file': str(self.duplicate_index_file),
            'logging': {
                'level': self.logging.level,
                'app_log_file': str(self.logging.app_log_file),
                'error_log_file': str(self.logging.error_log_file),
            },
        }

    @property
    def library_dir(self) -> Path:
        """Return the root folder used for exported post libraries."""

        return self.results_root / 'library'

    @property
    def state_dir(self) -> Path:
        """Return the root folder used for trackers, indexes, and run state."""

        return self.results_root / 'state'

    @property
    def logs_dir(self) -> Path:
        """Return the root folder used for runtime logs."""

        return self.results_root / 'logs'

    @property
    def organized_dir(self) -> Path:
        """Return the folder used for normally organized output."""

        return self.library_dir / 'Organized_Posts'

    @property
    def manual_dir(self) -> Path:
        """Return the folder used for posts requiring manual review."""

        return self.library_dir / 'Needs_Manual_Naming'

    @property
    def duplicates_dir(self) -> Path:
        """Return the folder used for duplicate-topic posts."""

        return self.library_dir / 'Duplicates'

    @property
    def workspace_dir(self) -> Path:
        """Return the parent directory for stable per-post workspaces."""

        return self.results_root / 'workspaces'

    @property
    def primary_tracker_file(self) -> Path:
        """Return the main processed-post tracker path."""

        return self.state_dir / 'progress.jsonl'

    @property
    def duplicate_tracker_file(self) -> Path:
        """Return the duplicate processed-post tracker path."""

        return self.state_dir / 'duplicates_progress.jsonl'

    @property
    def run_state_file(self) -> Path:
        """Return the persistent run-state file path."""

        return self.state_dir / 'run_state.json'

    @property
    def primary_index_file(self) -> Path:
        """Return the human-readable primary index path."""

        return self.state_dir / 'master_index.txt'

    @property
    def duplicate_index_file(self) -> Path:
        """Return the human-readable duplicate index path."""

        return self.state_dir / 'master_duplicates_index.txt'
