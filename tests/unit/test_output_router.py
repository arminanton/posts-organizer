from pathlib import Path

from instagram_organizer.domain.enums import OutputCategory
from instagram_organizer.infrastructure.filesystem.output_router import OutputRouter


def test_output_router_routes_manual_review(tmp_path: Path) -> None:
    router = OutputRouter(
        organized_dir=tmp_path / 'organized',
        manual_dir=tmp_path / 'manual',
        duplicates_dir=tmp_path / 'duplicates',
    )
    path = router.reserve_destination(
        category=OutputCategory.MANUAL_REVIEW,
        post_date='2026-03-08',
        title='MANUAL_REVIEW',
        shortcode='abc123',
    )
    assert path.parent == tmp_path / 'manual'
    assert 'abc123' in path.name


def test_output_router_creates_unique_duplicate_path(tmp_path: Path) -> None:
    router = OutputRouter(
        organized_dir=tmp_path / 'organized',
        manual_dir=tmp_path / 'manual',
        duplicates_dir=tmp_path / 'duplicates',
    )
    first = router.reserve_destination(
        category=OutputCategory.DUPLICATE,
        post_date='2026-03-08',
        title='Example Title',
        shortcode='abc123',
    )
    second = router.reserve_destination(
        category=OutputCategory.DUPLICATE,
        post_date='2026-03-08',
        title='Example Title',
        shortcode='abc123',
    )
    assert first != second
