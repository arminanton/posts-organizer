from pathlib import Path

from instagram_organizer.domain.enums import MediaType, OutputCategory, ProcessingStep
from instagram_organizer.domain.models import ProcessedPost, RunState
from instagram_organizer.infrastructure.filesystem.output_router import OutputRouter
from instagram_organizer.infrastructure.filesystem.workspace_manager import WorkspaceManager
from instagram_organizer.infrastructure.persistence.jsonl_tracker_repository import (
    JsonlTrackerRepository,
)
from instagram_organizer.infrastructure.persistence.run_state_repository import (
    RunStateJsonRepository,
)


def test_repositories_and_workspace_roundtrip(tmp_path: Path) -> None:
    workspace_manager = WorkspaceManager(tmp_path / 'workspaces')
    workspace = workspace_manager.prepare('abc123')
    run_state_repo = RunStateJsonRepository(tmp_path / 'run_state.json')
    run_state = RunState(
        shortcode='abc123',
        step=ProcessingStep.DOWNLOADING,
        workspace_path=workspace,
    )
    run_state_repo.save(run_state)
    assert run_state_repo.load() == run_state

    router = OutputRouter(
        organized_dir=tmp_path / 'organized',
        manual_dir=tmp_path / 'manual',
        duplicates_dir=tmp_path / 'duplicates',
    )
    destination = router.reserve_destination(
        category=OutputCategory.ORGANIZED,
        post_date='2026-03-08',
        title='Example Title',
        shortcode='abc123',
    )

    tracker = JsonlTrackerRepository(tmp_path / 'progress.jsonl')
    tracker.append(
        ProcessedPost(
            shortcode='abc123',
            title='Example Title',
            normalized_title='exampletitle',
            media_type=MediaType.IMAGE,
            date='2026-03-08',
            time='10:00:00 UTC',
            engagement='1.00%',
            hashtags='#x',
            timestamp=1.0,
            folder=str(destination.relative_to(tmp_path)),
            output_category=OutputCategory.ORGANIZED,
        )
    )
    assert tracker.load_records()[0].folder.startswith('organized/')
