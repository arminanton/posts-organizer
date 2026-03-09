from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from instagram_organizer.cli.commands import dispatch
from instagram_organizer.config.settings import AppSettings, LoggingSettings
from instagram_organizer.domain.enums import MediaType, OutputCategory, ProcessingStep
from instagram_organizer.domain.models import ProcessedPost, RunState
from instagram_organizer.infrastructure.persistence.jsonl_tracker_repository import JsonlTrackerRepository
from instagram_organizer.infrastructure.persistence.run_state_repository import RunStateJsonRepository



def test_cli_maintenance_commands_roundtrip(tmp_path: Path):
    settings = AppSettings(
        gemini_api_key="key",
        gemini_model="gemini-1.5-flash",
        target_account="acct",
        base_dir=tmp_path,
        results_root=tmp_path / 'results',
        ig_username=None,
        ig_session_file=tmp_path / 'results' / 'state' / '.ig_session',
        max_ai_images=10,
        gemini_inline_max_bytes=18_000_000,
        gemini_use_files_api=True,
        gemini_use_batch_fallback=True,
        logging=LoggingSettings(
            app_log_file=tmp_path / 'results' / 'logs' / 'app.log',
            error_log_file=tmp_path / 'results' / 'logs' / 'error.log',
        ),
    )
    tracker = JsonlTrackerRepository(settings.primary_tracker_file)
    duplicate_tracker = JsonlTrackerRepository(settings.duplicate_tracker_file)
    run_state_repo = RunStateJsonRepository(settings.run_state_file)

    tracker.append(
        ProcessedPost(
            shortcode="SHORT1",
            title="Topic One",
            normalized_title="topicone",
            media_type=MediaType.IMAGE,
            date="2026-03-09",
            time="10:00:00 UTC",
            engagement="2.00%",
            hashtags="",
            timestamp=1.0,
            folder="results/library/Organized_Posts/topic_one",
            output_category=OutputCategory.ORGANIZED,
        )
    )
    run_state_repo.save(
        RunState(
            shortcode="SHORT2",
            step=ProcessingStep.ANALYZING,
            workspace_path=settings.workspace_dir / 'SHORT2',
            partial_output_path=settings.organized_dir / 'topic_two',
            post_index=2,
            total_posts=10,
        )
    )

    rebuilt = dispatch(Namespace(command="rebuild-indexes"), settings)
    shown = dispatch(Namespace(command="show-run-state", json=False), settings)

    assert rebuilt == 0
    assert shown == 0
    assert settings.primary_index_file.exists()
    assert duplicate_tracker.load_records() == []
