"""Interface-style contracts for application services.

These protocols let orchestration code depend on abstractions rather than
concrete adapters. The design mirrors interface-driven architecture from Java
while staying idiomatic in Python.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Protocol, Sequence

from instagram_organizer.domain.models import AIAnalysis, ProcessedPost, RunState


class TitleAnalyzer(Protocol):
    """Analyze one Instagram post and produce a title plus rich reasoning."""

    def analyze(self, image_paths: Sequence[Path], caption: str = "") -> AIAnalysis:
        """Analyze post media and return structured AI analysis."""
        ...


class TrackerRepository(Protocol):
    """Persist and load successfully processed post records."""

    def load_records(self) -> list[ProcessedPost]:
        """Return all stored processed-post records."""
        ...

    def append(self, record: ProcessedPost) -> None:
        """Append a processed-post record to persistent storage."""
        ...

    def rewrite(self, records: list[ProcessedPost]) -> None:
        """Rewrite the full tracker canonically."""
        ...


class RunStateRepository(Protocol):
    """Persist recovery information for interrupted runs."""

    def load(self) -> RunState | None:
        """Return the latest saved run state, if present."""
        ...

    def save(self, state: RunState) -> None:
        """Persist a run-state snapshot."""
        ...

    def clear(self) -> None:
        """Remove the current run-state snapshot."""
        ...


class InstagramClient(Protocol):
    """Fetch profiles, iterate posts, and download media."""

    @property
    def loader(self) -> Any:
        """Return the underlying loader implementation if available."""
        ...

    def fetch_profile(self, username: str) -> Any:
        """Fetch a profile-like object for the requested username."""
        ...

    def iter_posts(self, profile: Any) -> Iterable[Any]:
        """Iterate all posts from a profile-like object."""
        ...

    def download_post(self, post: Any, workspace: Path) -> None:
        """Download one post into the provided workspace."""
        ...


class SessionStore(Protocol):
    """Load and persist Instagram session files."""

    def load(self, loader: Any, username: str) -> None:
        """Load a session into the provided loader."""
        ...

    def save(self, loader: Any) -> None:
        """Persist the current session from the provided loader."""
        ...


class Clock(Protocol):
    """Provide wall-clock values for easier testing of time-based logic."""

    def now_utc_iso(self) -> str:
        """Return the current UTC timestamp as an ISO-like string."""
        ...


class Sleeper(Protocol):
    """Abstraction for waiting or backoff logic."""

    def sleep(self, seconds: float) -> None:
        """Pause execution for the requested number of seconds."""
        ...
