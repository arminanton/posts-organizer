"""Pure business-domain services.

These helpers contain no filesystem, network, environment, or API side
effects. They are intentionally easy to test and re-use.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING

from instagram_organizer.domain.enums import OutputCategory

if TYPE_CHECKING:
    from instagram_organizer.domain.models import RunState


def normalize_title(title: str) -> str:
    """Normalize a title for duplicate detection.

    Args:
        title: Raw title string.

    Returns:
        A lowercase alphanumeric key suitable for O(1) hash-based lookup.

    Example:
        >>> normalize_title("Árvore of Life!")
        'arvoreoflife'
    """

    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", normalized.lower())


def sanitize_title_for_filesystem(title: str, max_len: int = 80) -> str:
    """Convert a free-form title into a filesystem-friendly folder segment."""

    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9 _-]", "", normalized)
    cleaned = re.sub(r"\s+", "_", cleaned).strip("._-")
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned[:max_len] or "UNTITLED"


def extract_hashtags(caption: str | None) -> tuple[str, ...]:
    """Extract hashtags from a caption as a de-duplicated ordered tuple."""

    if not caption:
        return ()

    seen: set[str] = set()
    ordered: list[str] = []
    for tag in re.findall(r"#(\w+)", caption):
        value = f"#{tag}"
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return tuple(ordered)


@dataclass(frozen=True, slots=True)
class OutputDecision:
    """Result of deciding where a processed post should be routed."""

    category: OutputCategory
    is_duplicate: bool
    requires_manual_review: bool


class OutputRoutingPolicy:
    """Pure policy for deciding output category.

    This is intentionally separate from filesystem routing. The policy decides
    *what* category a post belongs to; infrastructure later decides *where* to
    store it.
    """

    MANUAL_TITLES = frozenset({"MANUAL_REVIEW", "VIDEO_POST"})

    def decide(self, *, title: str, normalized_title: str, seen_titles: set[str]) -> OutputDecision:
        """Determine whether a post is organized, duplicate, or manual review."""

        if title in self.MANUAL_TITLES:
            return OutputDecision(
                category=OutputCategory.MANUAL_REVIEW,
                is_duplicate=False,
                requires_manual_review=True,
            )

        if normalized_title in seen_titles:
            return OutputDecision(
                category=OutputCategory.DUPLICATE,
                is_duplicate=True,
                requires_manual_review=False,
            )

        return OutputDecision(
            category=OutputCategory.ORGANIZED,
            is_duplicate=False,
            requires_manual_review=False,
        )


class RecoveryAdvisor:
    """Pure recovery heuristics for interrupted runs."""

    def should_retry_first(self, state: "RunState | None", processed_shortcodes: set[str]) -> bool:
        """Return whether the unfinished shortcode should be retried before the feed scan."""

        if state is None:
            return False
        return state.shortcode not in processed_shortcodes
