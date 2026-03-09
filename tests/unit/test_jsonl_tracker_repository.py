from pathlib import Path

from instagram_organizer.domain.enums import MediaType, OutputCategory
from instagram_organizer.domain.models import ProcessedPost
from instagram_organizer.infrastructure.persistence.jsonl_tracker_repository import (
    JsonlTrackerRepository,
)


def make_record(shortcode: str, title: str, timestamp: float) -> ProcessedPost:
    return ProcessedPost(
        shortcode=shortcode,
        title=title,
        normalized_title=title.lower().replace(' ', ''),
        media_type=MediaType.IMAGE,
        date='2026-03-08',
        time='10:00:00 UTC',
        engagement='1.00%',
        hashtags='#x',
        timestamp=timestamp,
        folder=f'Organized/{title}',
        output_category=OutputCategory.ORGANIZED,
    )


def test_tracker_append_and_load(tmp_path: Path) -> None:
    repo = JsonlTrackerRepository(tmp_path / 'progress.jsonl')
    repo.append(make_record('a1', 'One', 1.0))
    records = repo.load_records()
    assert [item.shortcode for item in records] == ['a1']


def test_tracker_rewrite_dedupes_by_shortcode(tmp_path: Path) -> None:
    repo = JsonlTrackerRepository(tmp_path / 'progress.jsonl')
    repo.rewrite([
        make_record('a1', 'Old', 1.0),
        make_record('a1', 'New', 2.0),
        make_record('b2', 'Two', 3.0),
    ])
    records = repo.load_records()
    assert [item.shortcode for item in records] == ['a1', 'b2']
    assert records[0].title == 'New'
