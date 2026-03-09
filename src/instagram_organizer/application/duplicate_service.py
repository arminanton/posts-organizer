"""Duplicate-detection utilities."""

from __future__ import annotations

from dataclasses import dataclass, field

from instagram_organizer.domain.models import ProcessedPost
from instagram_organizer.domain.services import normalize_title


@dataclass(slots=True)
class DuplicateService:
    """Track normalized titles for efficient duplicate detection."""

    seen_titles: set[str] = field(default_factory=set)

    def seed(self, records: list[ProcessedPost]) -> None:
        """Initialize duplicate state from existing processed records."""

        self.seen_titles = {record.normalized_title for record in records}

    def is_duplicate(self, normalized_title: str) -> bool:
        """Return whether the normalized title has already been seen."""

        return normalized_title in self.seen_titles

    def remember(self, normalized_title: str) -> None:
        """Record a normalized title as already processed."""

        self.seen_titles.add(normalized_title)

    def remember_title(self, title: str) -> None:
        """Normalize and store a raw title string."""

        self.seen_titles.add(normalize_title(title))
