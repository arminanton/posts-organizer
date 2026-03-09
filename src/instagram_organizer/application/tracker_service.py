"""Processed-post tracker service."""

from __future__ import annotations

from dataclasses import dataclass, field

from instagram_organizer.domain.models import ProcessedPost
from instagram_organizer.domain.protocols import TrackerRepository


@dataclass(slots=True)
class TrackerService:
    """Provide convenience operations over tracker persistence."""

    repository: TrackerRepository
    _records: list[ProcessedPost] = field(default_factory=list)

    def load(self) -> list[ProcessedPost]:
        """Load all processed records into memory."""

        self._records = self.repository.load_records()
        return list(self._records)

    def remember(self, record: ProcessedPost) -> None:
        """Persist a newly completed record."""

        self.repository.append(record)
        self._records.append(record)

    def shortcodes(self) -> set[str]:
        """Return all known processed shortcodes for O(1) membership checks."""

        return {record.shortcode for record in self._records}

    def records(self) -> list[ProcessedPost]:
        """Return the in-memory tracker snapshot."""

        return list(self._records)

    def rewrite(self) -> None:
        """Persist the canonical sorted tracker state."""

        self.repository.rewrite(self._records)
