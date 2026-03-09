from pathlib import Path

from instagram_organizer.domain.enums import ProcessingStep
from instagram_organizer.domain.models import RunState
from instagram_organizer.infrastructure.persistence.run_state_repository import (
    RunStateJsonRepository,
)


def test_run_state_roundtrip(tmp_path: Path) -> None:
    repo = RunStateJsonRepository(tmp_path / 'state.json')
    state = RunState(
        shortcode='abc123',
        step=ProcessingStep.DOWNLOADING,
        workspace_path=tmp_path / 'work',
        partial_output_path=tmp_path / 'out',
        post_index=3,
        total_posts=10,
    )
    repo.save(state)
    loaded = repo.load()
    assert loaded == state


def test_run_state_clear_removes_file(tmp_path: Path) -> None:
    repo = RunStateJsonRepository(tmp_path / 'state.json')
    repo.save(RunState(shortcode='abc123', step=ProcessingStep.STARTING))
    repo.clear()
    assert repo.load() is None
