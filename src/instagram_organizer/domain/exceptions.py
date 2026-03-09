"""Custom exception hierarchy for the organizer domain."""

from __future__ import annotations


class OrganizerError(Exception):
    """Base exception for all project-specific failures."""


class ConfigurationError(OrganizerError):
    """Raised when required configuration is missing or invalid."""


class ValidationError(OrganizerError):
    """Raised when a domain model receives invalid data."""


class RecoveryError(OrganizerError):
    """Raised when recovery state cannot be applied safely."""


class AnalysisError(OrganizerError):
    """Raised when AI response handling fails irrecoverably."""


class PersistenceError(OrganizerError):
    """Raised when a repository cannot read or write domain state."""
