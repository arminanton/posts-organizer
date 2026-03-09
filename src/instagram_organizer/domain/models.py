"""Core value objects for the organizer domain.

The domain layer contains pure, side-effect-free data structures. These models
provide validation plus serialization helpers so repositories can stay thin.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from instagram_organizer.domain.enums import (
    DominantSignal,
    MediaType,
    OutputCategory,
    ProcessingStep,
)
from instagram_organizer.domain.exceptions import ValidationError
from instagram_organizer.domain.services import normalize_title


@dataclass(frozen=True, slots=True)
class PostIdentity:
    """Stable identifiers for a single Instagram post.

    Args:
        shortcode: Instagram shortcode uniquely identifying the post.
        date_utc: Original UTC post date as a string.
    """

    shortcode: str
    date_utc: str

    def __post_init__(self) -> None:
        if not self.shortcode.strip():
            raise ValidationError("shortcode must not be empty")
        if not self.date_utc.strip():
            raise ValidationError("date_utc must not be empty")


@dataclass(frozen=True, slots=True)
class AIAnalysis:
    """Structured result returned by the title analysis engine.

    The raw payload is preserved for debugging and future reprocessing, while the
    typed fields are used by the application workflow.
    """

    title: str
    dominant_signal: DominantSignal = DominantSignal.UNCERTAIN
    per_image_analysis: tuple[str, ...] = ()
    ocr_summary: str = ""
    combined_analysis: str = ""
    raw_payload: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValidationError("AIAnalysis.title must not be empty")

    @property
    def normalized_title(self) -> str:
        """Return a stable duplicate-detection key for the title."""

        return normalize_title(self.title)

    @property
    def is_manual_review(self) -> bool:
        """Return whether the AI marked the post for manual review."""

        return self.title.upper() == "MANUAL_REVIEW"

    def to_dict(self) -> dict[str, Any]:
        """Serialize this analysis to a JSON-friendly dictionary."""

        return {
            "title": self.title,
            "dominant_signal": self.dominant_signal.value,
            "per_image_analysis": list(self.per_image_analysis),
            "ocr_summary": self.ocr_summary,
            "combined_analysis": self.combined_analysis,
            "raw_payload": dict(self.raw_payload),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AIAnalysis":
        """Create an analysis object from a parsed dictionary."""

        signal_text = str(data.get("dominant_signal", DominantSignal.UNCERTAIN.value))
        try:
            signal = DominantSignal(signal_text)
        except ValueError:
            signal = DominantSignal.UNCERTAIN

        return cls(
            title=str(data.get("title", "")).strip() or "MANUAL_REVIEW",
            dominant_signal=signal,
            per_image_analysis=tuple(str(item) for item in data.get("per_image_analysis", [])),
            ocr_summary=str(data.get("ocr_summary", "")),
            combined_analysis=str(data.get("combined_analysis", "")),
            raw_payload=dict(data.get("raw_payload", data)),
        )


@dataclass(frozen=True, slots=True)
class ProcessedPost:
    """Persistent record for a successfully processed post.

    Example:
        >>> record = ProcessedPost(
        ...     shortcode="abc123",
        ...     title="Solar Eclipse Physics Explained",
        ...     normalized_title="solareclipsephysicsexplained",
        ...     media_type=MediaType.IMAGE,
        ...     date="2026-03-08",
        ...     time="10:00:00 UTC",
        ...     engagement="2.34%",
        ...     hashtags="#space",
        ...     timestamp=1.0,
        ...     folder="Organized_Posts/Solar_Eclipse_Physics_Explained",
        ... )
        >>> record.shortcode
        'abc123'
    """

    shortcode: str
    title: str
    normalized_title: str
    media_type: MediaType
    date: str
    time: str
    engagement: str
    hashtags: str
    timestamp: float
    folder: str
    output_category: OutputCategory = OutputCategory.ORGANIZED

    def __post_init__(self) -> None:
        if not self.shortcode.strip():
            raise ValidationError("ProcessedPost.shortcode must not be empty")
        if not self.title.strip():
            raise ValidationError("ProcessedPost.title must not be empty")
        if not self.normalized_title.strip():
            raise ValidationError(
                "ProcessedPost.normalized_title must not be empty"
            )
        if self.timestamp < 0:
            raise ValidationError("ProcessedPost.timestamp must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the record to a JSON-friendly dictionary."""

        return {
            "shortcode": self.shortcode,
            "title": self.title,
            "normalized_title": self.normalized_title,
            "media_type": self.media_type.value,
            "date": self.date,
            "time": self.time,
            "engagement": self.engagement,
            "hashtags": self.hashtags,
            "timestamp": self.timestamp,
            "folder": self.folder,
            "output_category": self.output_category.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProcessedPost":
        """Create a processed-post record from a parsed dictionary."""

        return cls(
            shortcode=str(data["shortcode"]),
            title=str(data["title"]),
            normalized_title=str(data.get("normalized_title") or normalize_title(str(data["title"]))),
            media_type=MediaType(str(data.get("media_type", MediaType.UNKNOWN.value))),
            date=str(data["date"]),
            time=str(data["time"]),
            engagement=str(data["engagement"]),
            hashtags=str(data.get("hashtags", "")),
            timestamp=float(data["timestamp"]),
            folder=str(data["folder"]),
            output_category=OutputCategory(
                str(data.get("output_category", OutputCategory.ORGANIZED.value))
            ),
        )


@dataclass(frozen=True, slots=True)
class RunState:
    """State describing a partially completed in-flight post.

    This object is intentionally small. It should be enough to recover or clean
    up an interrupted post without duplicating the full tracker data.
    """

    shortcode: str
    step: ProcessingStep
    workspace_path: Path | None = None
    partial_output_path: Path | None = None
    post_index: int | None = None
    total_posts: int | None = None

    def __post_init__(self) -> None:
        if not self.shortcode.strip():
            raise ValidationError("RunState.shortcode must not be empty")
        if self.post_index is not None and self.post_index < 1:
            raise ValidationError("RunState.post_index must be >= 1")
        if self.total_posts is not None and self.total_posts < 1:
            raise ValidationError("RunState.total_posts must be >= 1")

    @property
    def is_recoverable(self) -> bool:
        """Return whether this state contains enough information to attempt recovery."""

        return self.workspace_path is not None or self.partial_output_path is not None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the run state to a JSON-friendly dictionary."""

        return {
            "shortcode": self.shortcode,
            "step": self.step.value,
            "workspace_path": str(self.workspace_path) if self.workspace_path else None,
            "partial_output_path": (
                str(self.partial_output_path) if self.partial_output_path else None
            ),
            "post_index": self.post_index,
            "total_posts": self.total_posts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunState":
        """Create a run-state object from a parsed dictionary."""

        return cls(
            shortcode=str(data["shortcode"]),
            step=ProcessingStep(str(data["step"])),
            workspace_path=Path(data["workspace_path"]) if data.get("workspace_path") else None,
            partial_output_path=(
                Path(data["partial_output_path"])
                if data.get("partial_output_path")
                else None
            ),
            post_index=(int(data["post_index"]) if data.get("post_index") is not None else None),
            total_posts=(
                int(data["total_posts"]) if data.get("total_posts") is not None else None
            ),
        )
