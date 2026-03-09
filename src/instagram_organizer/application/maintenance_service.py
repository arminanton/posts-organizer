"""Application maintenance workflows.

These use cases support operators with non-scraping tasks such as rebuilding
indexes and inspecting or clearing recovery state.
"""

from __future__ import annotations

from dataclasses import dataclass

from instagram_organizer.application.index_service import IndexService
from instagram_organizer.application.tracker_service import TrackerService
from instagram_organizer.domain.models import RunState
from instagram_organizer.domain.protocols import RunStateRepository


@dataclass(slots=True)
class MaintenanceService:
    """Perform operational maintenance actions.

    Args:
        primary_tracker: Service for the main tracker.
        duplicate_tracker: Service for duplicate tracker records.
        index_service: Index writer service.
        run_state_repository: Recovery-state repository.
    """

    primary_tracker: TrackerService
    duplicate_tracker: TrackerService
    index_service: IndexService
    run_state_repository: RunStateRepository

    def rebuild_indexes(self) -> tuple[int, int]:
        """Reload tracker state and rebuild all summary indexes.

        Returns:
            A pair of counts ``(primary_count, duplicate_count)``.
        """

        primary_records = self.primary_tracker.load()
        duplicate_records = self.duplicate_tracker.load()
        self.index_service.write(primary_records, duplicate_records)
        return len(primary_records), len(duplicate_records)

    def load_run_state(self) -> RunState | None:
        """Return the current persisted run state, if any."""

        return self.run_state_repository.load()

    def clear_run_state(self) -> bool:
        """Delete the persisted run state.

        Returns:
            ``True`` if a state file existed and was cleared, otherwise ``False``.
        """

        existed = self.run_state_repository.load() is not None
        self.run_state_repository.clear()
        return existed
