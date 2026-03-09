from pathlib import Path

from instagram_organizer.application.recovery_service import RecoveryService
from instagram_organizer.domain.enums import ProcessingStep
from instagram_organizer.domain.models import RunState
from instagram_organizer.infrastructure.filesystem.output_router import OutputRouter
from instagram_organizer.infrastructure.persistence.run_state_repository import RunStateJsonRepository


class FakePost:
    def __init__(self, shortcode: str) -> None:
        self.shortcode = shortcode


def test_recovery_service_reorders_unfinished_post_first(tmp_path: Path) -> None:
    router = OutputRouter(tmp_path / 'organized', tmp_path / 'manual', tmp_path / 'duplicates')
    service = RecoveryService(RunStateJsonRepository(tmp_path / 'state.json'), router)
    state = RunState(shortcode='b2', step=ProcessingStep.DOWNLOADING)
    posts = lambda: [FakePost('a1'), FakePost('b2'), FakePost('c3')]

    ordered = [post.shortcode for post in service.reorder_posts(posts, state, processed_shortcodes=set())]
    assert ordered == ['b2', 'a1', 'c3']


def test_recovery_service_cleans_partial_output(tmp_path: Path) -> None:
    router = OutputRouter(tmp_path / 'organized', tmp_path / 'manual', tmp_path / 'duplicates')
    service = RecoveryService(RunStateJsonRepository(tmp_path / 'state.json'), router)
    partial = tmp_path / 'manual' / 'stale'
    partial.mkdir(parents=True)
    service.cleanup_partial_output(
        RunState(shortcode='a1', step=ProcessingStep.WRITING_FILES, partial_output_path=partial)
    )
    assert not partial.exists()
