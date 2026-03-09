from pathlib import Path

from instagram_organizer.application.tracker_service import TrackerService
from instagram_organizer.domain.enums import MediaType
from instagram_organizer.domain.models import ProcessedPost
from instagram_organizer.infrastructure.persistence.jsonl_tracker_repository import (
    JsonlTrackerRepository,
)


def test_tracker_service_roundtrip(tmp_path: Path) -> None:
    repository = JsonlTrackerRepository(tmp_path / "progress.jsonl")
    service = TrackerService(repository=repository)

    record = ProcessedPost(
        shortcode="xyz",
        title="Example",
        normalized_title="example",
        media_type=MediaType.IMAGE,
        date="2026-03-08",
        time="10:00:00 UTC",
        engagement="3.21%",
        hashtags="#tag",
        timestamp=2.0,
        folder="Organized_Posts/Example",
    )
    service.remember(record)

    loaded = service.load()
    assert len(loaded) == 1
    assert loaded[0].shortcode == "xyz"
