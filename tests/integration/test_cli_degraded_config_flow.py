from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from instagram_organizer.cli.commands import dispatch
from instagram_organizer.config.settings import AppSettings, LoggingSettings
from instagram_organizer.domain.enums import ProcessingStep
from instagram_organizer.domain.models import RunState
from instagram_organizer.infrastructure.persistence.run_state_repository import RunStateJsonRepository


def test_show_run_state_and_clear_work_without_runtime_secrets(tmp_path: Path) -> None:
    settings = AppSettings.from_sources(
        overrides={'BASE_DIR': str(tmp_path)},
        strict=False,
    )
    run_state_repo = RunStateJsonRepository(settings.run_state_file)
    run_state_repo.save(
        RunState(
            shortcode='SHORTX',
            step=ProcessingStep.ANALYZING,
            workspace_path=tmp_path / '.tmp_work' / 'SHORTX',
            partial_output_path=tmp_path / 'Organized_Posts' / 'topic_x',
            post_index=1,
            total_posts=99,
        )
    )

    shown = dispatch(Namespace(command='show-run-state', json=True), settings)
    cleared = dispatch(Namespace(command='clear-run-state'), settings)

    assert shown == 0
    assert cleared == 0
    assert run_state_repo.load() is None
