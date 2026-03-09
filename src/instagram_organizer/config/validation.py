"""Configuration validation helpers.

This module keeps environment validation separate from loading logic so the CLI
can present friendly diagnostics without touching application internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from instagram_organizer.config.settings import AppSettings


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One validation finding.

    Args:
        field_name: Name of the setting or subsystem involved.
        message: Human-readable diagnostic message.
        severity: Either ``error`` or ``warning``.
    """

    field_name: str
    message: str
    severity: str = 'warning'


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Aggregate validation result for application settings."""

    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        """Return only error-level issues."""

        return tuple(issue for issue in self.issues if issue.severity == 'error')

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        """Return only warning-level issues."""

        return tuple(issue for issue in self.issues if issue.severity != 'error')

    @property
    def is_valid(self) -> bool:
        """Return whether the report contains no errors."""

        return not self.errors


def validate_settings(settings: AppSettings) -> ValidationReport:
    """Validate resolved settings for operator-facing diagnostics.

    Args:
        settings: Loaded application settings.

    Returns:
        A report containing warnings and errors.
    """

    issues: list[ValidationIssue] = []

    if not settings.gemini_api_key.strip():
        issues.append(ValidationIssue('GEMINI_API_KEY', 'Gemini API key is empty.', 'error'))
    if not settings.target_account.strip():
        issues.append(ValidationIssue('TARGET_ACCOUNT', 'Target account is empty.', 'error'))
    if settings.max_ai_images < 1:
        issues.append(ValidationIssue('MAX_AI_IMAGES', 'MAX_AI_IMAGES must be at least 1.', 'error'))

    if not settings.base_dir.exists():
        issues.append(
            ValidationIssue(
                'BASE_DIR',
                f'Base directory does not exist yet and will be created on first run: {settings.base_dir}',
                'warning',
            )
        )
    elif not settings.base_dir.is_dir():
        issues.append(ValidationIssue('BASE_DIR', 'Base path is not a directory.', 'error'))

    results_parent = settings.results_root.parent
    if results_parent.exists() and not results_parent.is_dir():
        issues.append(
            ValidationIssue(
                'RESULTS_DIR',
                f'Parent path is not a directory: {results_parent}',
                'error',
            )
        )

    if settings.ig_username and not settings.ig_session_file.exists():
        issues.append(
            ValidationIssue(
                'IG_SESSION_FILE',
                f'Session file does not exist yet: {settings.ig_session_file}',
                'warning',
            )
        )

    for path_name, path in {
        'APP_LOG_FILE': Path(settings.logging.app_log_file),
        'ERROR_LOG_FILE': Path(settings.logging.error_log_file),
    }.items():
        parent = path.parent
        if parent.exists() and not parent.is_dir():
            issues.append(ValidationIssue(path_name, f'Parent path is not a directory: {parent}', 'error'))

    return ValidationReport(tuple(issues))
