"""Thin Instaloader adapter.

This module isolates direct imports and method names from the rest of the
application, making the Instagram integration easier to fake in tests and swap
later if needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable


LoaderFactory = Callable[..., Any]
ProfileResolver = Callable[[Any, str], Any]


@dataclass(slots=True)
class InstaloaderClient:
    """Wrapper for Instaloader operations used by the application."""

    loader_factory: LoaderFactory | None = None
    profile_resolver: ProfileResolver | None = None
    download_video_thumbnails: bool = True
    save_metadata: bool = True
    post_metadata_txt_pattern: str = ""
    _loader: Any = field(default=None, init=False, repr=False)

    @property
    def loader(self) -> Any:
        """Return the lazily constructed Instaloader instance."""

        if self._loader is None:
            self._loader = self._create_loader()
        return self._loader

    def fetch_profile(self, username: str) -> Any:
        """Fetch one Instagram profile object for the requested username."""

        resolver = self.profile_resolver
        if resolver is None:
            import instaloader  # type: ignore

            resolver = instaloader.Profile.from_username
        return resolver(self.loader.context, username)

    def iter_posts(self, profile: Any) -> Iterable[Any]:
        """Return the iterable of posts for a profile-like object."""

        return profile.get_posts()

    def download_post(self, post: Any, workspace: Path) -> None:
        """Download one post into the given workspace directory."""

        self.loader.download_post(post, target=str(workspace))

    def login(self, username: str, password: str) -> None:
        """Authenticate the underlying Instaloader client interactively."""

        self.loader.login(username, password)

    def two_factor_login(self, code: str) -> None:
        """Complete an interactive two-factor login flow when required."""

        self.loader.two_factor_login(code)

    def test_login(self) -> str | None:
        """Return the logged-in username if Instaloader can determine it."""

        tester = getattr(self.loader, 'test_login', None)
        if callable(tester):
            return tester()
        context = getattr(self.loader, 'context', None)
        username = getattr(context, 'username', None)
        return str(username) if username else None

    def _create_loader(self) -> Any:
        """Create the concrete Instaloader instance lazily."""

        factory = self.loader_factory
        if factory is None:
            import instaloader  # type: ignore

            factory = instaloader.Instaloader
        return factory(
            download_video_thumbnails=self.download_video_thumbnails,
            save_metadata=self.save_metadata,
            post_metadata_txt_pattern=self.post_metadata_txt_pattern,
        )
