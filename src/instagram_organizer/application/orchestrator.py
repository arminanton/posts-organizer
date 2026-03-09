"""Top-level application use-case orchestration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from instagram_organizer.application.runtime import ApplicationRuntime
from instagram_organizer.config.settings import AppSettings


@dataclass(slots=True)
class Orchestrator:
    """Coordinate the main end-to-end workflow."""

    settings: AppSettings
    runtime: ApplicationRuntime
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger('instagram_organizer')
    )

    def run(self) -> int:
        """Run the application and return a process exit code."""

        self._ensure_session_loaded()
        primary_records = self.runtime.primary_tracker.load()
        duplicate_records = self.runtime.duplicate_tracker.load()
        self.runtime.duplicate_service.seed(primary_records + duplicate_records)

        processed_shortcodes = (
            self.runtime.primary_tracker.shortcodes() | self.runtime.duplicate_tracker.shortcodes()
        )
        state = self.runtime.recovery_service.load()
        self.logger.info(self.runtime.recovery_service.describe(state))
        self.runtime.recovery_service.cleanup_partial_output(state)

        profile = self.runtime.instagram_client.fetch_profile(self.settings.target_account)
        total_posts = int(getattr(profile, 'mediacount', 0) or 0)
        total_followers = int(getattr(profile, 'followers', 0) or 0)
        self.logger.info('Target %s: %s posts, %s followers', self.settings.target_account, total_posts, total_followers)

        posts_factory: Callable[[], Any] = lambda: self.runtime.instagram_client.iter_posts(profile)
        index = 0
        for index, post in enumerate(
            self.runtime.recovery_service.reorder_posts(posts_factory, state, processed_shortcodes),
            start=1,
        ):
            shortcode = str(getattr(post, 'shortcode', ''))
            if shortcode in processed_shortcodes:
                self.logger.info('Skipping previously processed post %s', shortcode)
                continue

            record = self.runtime.post_processor.process(
                post=post,
                total_followers=total_followers,
                post_index=index,
                total_posts=total_posts or index,
                reuse_workspace=self.runtime.recovery_service.reuse_workspace(state, shortcode),
            )
            processed_shortcodes.add(shortcode)
            if record.output_category.value == 'duplicate':
                self.runtime.duplicate_tracker.remember(record)
            else:
                self.runtime.primary_tracker.remember(record)
            if record.output_category.value != 'manual_review':
                self.runtime.duplicate_service.remember(record.normalized_title)
            self.logger.info('Processed %s into %s', record.shortcode, record.folder)
            state = None

        self.runtime.primary_tracker.rewrite()
        self.runtime.duplicate_tracker.rewrite()
        self.runtime.index_service.write(
            self.runtime.primary_tracker.records(),
            self.runtime.duplicate_tracker.records(),
        )
        self._persist_session_snapshot()
        self.logger.info('Run finished after %s iterations.', index)
        return 0

    def _ensure_session_loaded(self) -> None:
        if self.settings.ig_username and self.runtime.session_store is not None:
            try:
                self.runtime.session_store.load(
                    self.runtime.instagram_client.loader,
                    self.settings.ig_username,
                )
                self.logger.info('Loaded Instagram session for %s', self.settings.ig_username)
            except FileNotFoundError:
                self.logger.warning('Session file not found. Run `instagram-organizer login` to create one, or continue without a saved session.')
            except Exception:
                self.logger.warning('Could not load saved Instagram session.', exc_info=True)

    def _persist_session_snapshot(self) -> None:
        if self.settings.ig_username and self.runtime.session_store is not None:
            try:
                self.runtime.session_store.save(self.runtime.instagram_client.loader)
            except Exception:
                self.logger.warning('Could not persist Instagram session snapshot.', exc_info=True)
