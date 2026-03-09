from pathlib import Path

from instagram_organizer.application.index_service import IndexService
from instagram_organizer.application.maintenance_service import MaintenanceService
from instagram_organizer.application.tracker_service import TrackerService
from instagram_organizer.domain.enums import MediaType, OutputCategory, ProcessingStep
from instagram_organizer.domain.models import ProcessedPost, RunState
from instagram_organizer.infrastructure.persistence.jsonl_tracker_repository import JsonlTrackerRepository
from instagram_organizer.infrastructure.persistence.run_state_repository import RunStateJsonRepository


def make_record(shortcode: str, title: str, folder: str, category: OutputCategory) -> ProcessedPost:
    return ProcessedPost(
        shortcode=shortcode,
        title=title,
        normalized_title=title.lower().replace(' ', ''),
        media_type=MediaType.IMAGE,
        date='2026-03-08',
        time='12:00:00 UTC',
        engagement='1.00%',
        hashtags='#tag',
        timestamp=1.0,
        folder=folder,
        output_category=category,
    )


def test_rebuild_indexes_writes_index_files(tmp_path: Path) -> None:
    primary = TrackerService(JsonlTrackerRepository(tmp_path / 'progress.jsonl'))
    duplicate = TrackerService(JsonlTrackerRepository(tmp_path / 'duplicates.jsonl'))
    primary.remember(make_record('a1', 'Title One', 'Organized_Posts/one', OutputCategory.ORGANIZED))
    duplicate.remember(make_record('b2', 'Title Two', 'Duplicates/two', OutputCategory.DUPLICATE))
    service = MaintenanceService(
        primary_tracker=primary,
        duplicate_tracker=duplicate,
        index_service=IndexService(tmp_path / 'master.txt', tmp_path / 'duplicates.txt'),
        run_state_repository=RunStateJsonRepository(tmp_path / 'run_state.json'),
    )
    counts = service.rebuild_indexes()
    assert counts == (1, 1)
    assert (tmp_path / 'master.txt').exists()
    assert (tmp_path / 'duplicates.txt').exists()


def test_clear_run_state_reports_existence(tmp_path: Path) -> None:
    repository = RunStateJsonRepository(tmp_path / 'run_state.json')
    repository.save(RunState(shortcode='abc123', step=ProcessingStep.DOWNLOADING))
    service = MaintenanceService(
        primary_tracker=TrackerService(JsonlTrackerRepository(tmp_path / 'progress.jsonl')),
        duplicate_tracker=TrackerService(JsonlTrackerRepository(tmp_path / 'duplicates.jsonl')),
        index_service=IndexService(tmp_path / 'master.txt', tmp_path / 'duplicates.txt'),
        run_state_repository=repository,
    )
    assert service.clear_run_state() is True
    assert service.load_run_state() is None
