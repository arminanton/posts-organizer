"""Domain enumerations.

These enums capture stable concepts shared across application and
infrastructure layers. Keeping them in one place prevents stringly-typed
logic from spreading through the project.
"""

from __future__ import annotations

from enum import StrEnum


class MediaType(StrEnum):
    """Supported Instagram media classifications."""

    IMAGE = "image"
    VIDEO = "video"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class DominantSignal(StrEnum):
    """Primary signal the AI used to understand the post."""

    VISUAL = "visual"
    TEXT = "text"
    BALANCED = "balanced"
    UNCERTAIN = "uncertain"


class OutputCategory(StrEnum):
    """High-level destination category for a processed post."""

    ORGANIZED = "organized"
    DUPLICATE = "duplicate"
    MANUAL_REVIEW = "manual_review"


class ProcessingStep(StrEnum):
    """Major checkpoints for recovery and observability."""

    STARTING = "starting"
    DOWNLOADING = "downloading"
    ANALYZING = "analyzing"
    WRITING_FILES = "writing_files"
    COMPLETED = "completed"
