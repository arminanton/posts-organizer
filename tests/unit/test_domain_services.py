from instagram_organizer.domain.enums import OutputCategory, ProcessingStep
from instagram_organizer.domain.models import RunState
from instagram_organizer.domain.services import (
    OutputRoutingPolicy,
    RecoveryAdvisor,
    extract_hashtags,
    normalize_title,
    sanitize_title_for_filesystem,
)


def test_normalize_title_and_filesystem_sanitization() -> None:
    assert normalize_title("Árvore of Life!") == "arvoreoflife"
    assert sanitize_title_for_filesystem("A/B Test: Vision & Text") == "AB_Test_Vision_Text"


def test_extract_hashtags_preserves_order_and_uniqueness() -> None:
    assert extract_hashtags("#one #two #one") == ("#one", "#two")
    assert extract_hashtags(None) == ()


def test_output_routing_policy_decides_manual_duplicate_and_organized() -> None:
    policy = OutputRoutingPolicy()

    manual = policy.decide(title="MANUAL_REVIEW", normalized_title="manualreview", seen_titles=set())
    duplicate = policy.decide(title="Example", normalized_title="example", seen_titles={"example"})
    organized = policy.decide(title="Example", normalized_title="example", seen_titles=set())

    assert manual.category == OutputCategory.MANUAL_REVIEW
    assert manual.requires_manual_review is True
    assert duplicate.category == OutputCategory.DUPLICATE
    assert duplicate.is_duplicate is True
    assert organized.category == OutputCategory.ORGANIZED


def test_recovery_advisor_retries_only_unprocessed_state() -> None:
    advisor = RecoveryAdvisor()
    state = RunState(shortcode="abc", step=ProcessingStep.DOWNLOADING)

    assert advisor.should_retry_first(state, processed_shortcodes=set()) is True
    assert advisor.should_retry_first(state, processed_shortcodes={"abc"}) is False
    assert advisor.should_retry_first(None, processed_shortcodes=set()) is False
