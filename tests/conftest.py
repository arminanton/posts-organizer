from __future__ import annotations

from pathlib import Path

import pytest

from instagram_organizer.config.settings import AppSettings, LoggingSettings
from instagram_organizer.domain.enums import MediaType, OutputCategory
from instagram_organizer.domain.models import ProcessedPost


@pytest.fixture()
def sample_settings(tmp_path: Path) -> AppSettings:
    base_dir = tmp_path / "project"
    results_root = base_dir / "results"
    return AppSettings(
        gemini_api_key="test-key",
        gemini_model="gemini-1.5-flash",
        target_account="target-account",
        base_dir=base_dir,
        results_root=results_root,
        ig_username="sample-user",
        ig_session_file=results_root / "state" / ".ig_session",
        max_ai_images=10,
        gemini_inline_max_bytes=18_000_000,
        gemini_use_files_api=True,
        gemini_use_batch_fallback=True,
        logging=LoggingSettings(
            app_log_file=results_root / "logs" / "app.log",
            error_log_file=results_root / "logs" / "error.log",
        ),
    )


@pytest.fixture()
def sample_record() -> ProcessedPost:
    return ProcessedPost(
        shortcode="ABC123",
        title="Sample Educational Topic",
        normalized_title="sampleeducationaltopic",
        media_type=MediaType.IMAGE,
        date="2026-03-09",
        time="12:00:00 UTC",
        engagement="1.23%",
        hashtags="#education, #science",
        timestamp=1700000000.0,
        folder="results/library/Organized_Posts/2026-03-09_Sample_Educational_Topic",
        output_category=OutputCategory.ORGANIZED,
    )
