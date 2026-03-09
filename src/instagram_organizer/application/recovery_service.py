"""Recovery orchestration utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from instagram_organizer.domain.models import RunState
from instagram_organizer.domain.protocols import RunStateRepository
from instagram_organizer.domain.services import RecoveryAdvisor
from instagram_organizer.infrastructure.filesystem.output_router import OutputRouter


@dataclass(slots=True)
class RecoveryService:
    """Interpret and apply recovery state."""

    repository: RunStateRepository
    output_router: OutputRouter
    advisor: RecoveryAdvisor = RecoveryAdvisor()

    def load(self) -> RunState | None:
        """Return the latest persisted run state, if any."""

        return self.repository.load()

    def describe(self, state: RunState | None) -> str:
        """Return a user-facing summary of the recovery state."""

        if state is None:
            return "No previous interrupted run."
        return f"Interrupted post {state.shortcode} at step {state.step.value}."

    def should_retry_first(self, state: RunState | None, processed_shortcodes: set[str]) -> bool:
        """Return whether the unfinished post should be retried before normal iteration."""

        return self.advisor.should_retry_first(state, processed_shortcodes)

    def cleanup_partial_output(self, state: RunState | None) -> None:
        """Remove any partially written destination folder from the prior run."""

        if state is None:
            return
        self.output_router.cleanup_partial(state.partial_output_path)

    def reuse_workspace(self, state: RunState | None, shortcode: str) -> bool:
        """Return whether an existing workspace should be reused for the shortcode."""

        return bool(
            state
            and state.shortcode == shortcode
            and state.workspace_path is not None
            and state.workspace_path.exists()
        )

    def reorder_posts(
        self,
        posts_factory: callable,
        state: RunState | None,
        processed_shortcodes: set[str],
    ) -> Iterable[Any]:
        """Yield posts with any unfinished shortcode processed first.

        Args:
            posts_factory: Zero-argument callable returning a fresh post iterable.
            state: Previously persisted run state.
            processed_shortcodes: Already completed post shortcodes.
        """

        if not self.should_retry_first(state, processed_shortcodes):
            yield from posts_factory()
            return

        assert state is not None
        retry_shortcode = state.shortcode
        for post in posts_factory():
            if str(getattr(post, 'shortcode', '')) == retry_shortcode:
                yield post
                break

        for post in posts_factory():
            if str(getattr(post, 'shortcode', '')) != retry_shortcode:
                yield post
