from pathlib import Path

import pytest

from instagram_organizer.domain.enums import DominantSignal, MediaType, OutputCategory, ProcessingStep
from instagram_organizer.domain.exceptions import ValidationError
from instagram_organizer.domain.models import AIAnalysis, ProcessedPost, RunState


def test_ai_analysis_normalizes_title_and_detects_manual_review() -> None:
    analysis = AIAnalysis(
        title="Árvore of Life",
        dominant_signal=DominantSignal.VISUAL,
        per_image_analysis=("img1",),
    )
    assert analysis.normalized_title == "arvoreoflife"
    assert analysis.is_manual_review is False

    manual = AIAnalysis(title="MANUAL_REVIEW")
    assert manual.is_manual_review is True


def test_processed_post_roundtrip_preserves_output_category() -> None:
    record = ProcessedPost(
        shortcode="abc123",
        title="Example",
        normalized_title="example",
        media_type=MediaType.IMAGE,
        date="2026-03-08",
        time="10:00:00 UTC",
        engagement="1.00%",
        hashtags="#tag",
        timestamp=1.0,
        folder="Organized_Posts/Example",
        output_category=OutputCategory.DUPLICATE,
    )

    restored = ProcessedPost.from_dict(record.to_dict())
    assert restored == record


def test_run_state_roundtrip_and_recoverable_property() -> None:
    state = RunState(
        shortcode="post1",
        step=ProcessingStep.ANALYZING,
        workspace_path=Path("/tmp/work"),
        partial_output_path=Path("/tmp/out"),
        post_index=5,
        total_posts=10,
    )

    restored = RunState.from_dict(state.to_dict())
    assert restored == state
    assert restored.is_recoverable is True


def test_processed_post_requires_non_empty_shortcode() -> None:
    with pytest.raises(ValidationError):
        ProcessedPost(
            shortcode="",
            title="Example",
            normalized_title="example",
            media_type=MediaType.IMAGE,
            date="2026-03-08",
            time="10:00:00 UTC",
            engagement="1.00%",
            hashtags="",
            timestamp=1.0,
            folder="Organized_Posts/Example",
        )
