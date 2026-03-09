"""Concrete application runtime wiring."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from instagram_organizer.application.ai_analysis_service import AIAnalysisService
from instagram_organizer.application.duplicate_service import DuplicateService
from instagram_organizer.application.index_service import IndexService
from instagram_organizer.application.post_processor import PostProcessor
from instagram_organizer.application.recovery_service import RecoveryService
from instagram_organizer.application.tracker_service import TrackerService
from instagram_organizer.domain.protocols import InstagramClient, SessionStore


@dataclass(slots=True)
class ApplicationRuntime:
    """Concrete services and adapters required by the orchestrator."""

    instagram_client: InstagramClient
    session_store: SessionStore | None
    ai_analysis_service: AIAnalysisService
    primary_tracker: TrackerService
    duplicate_tracker: TrackerService
    duplicate_service: DuplicateService
    recovery_service: RecoveryService
    post_processor: PostProcessor
    index_service: IndexService
    logger: logging.Logger
