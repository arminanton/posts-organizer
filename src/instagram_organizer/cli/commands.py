"""CLI command orchestration helpers.

This module isolates command dispatch from parser construction and runtime
wiring so both remain testable and easy to evolve.
"""

from __future__ import annotations

import json
import logging
from argparse import Namespace
from typing import Any

from instagram_organizer.application.ai_analysis_service import AIAnalysisService
from instagram_organizer.application.auth_service import AuthService
from instagram_organizer.application.duplicate_service import DuplicateService
from instagram_organizer.application.index_service import IndexService
from instagram_organizer.application.maintenance_service import MaintenanceService
from instagram_organizer.application.orchestrator import Orchestrator
from instagram_organizer.application.post_processor import PostProcessor
from instagram_organizer.application.recovery_service import RecoveryService
from instagram_organizer.application.runtime import ApplicationRuntime
from instagram_organizer.application.tracker_service import TrackerService
from instagram_organizer.config.settings import AppSettings
from instagram_organizer.config.validation import validate_settings
from instagram_organizer.domain.services import OutputRoutingPolicy
from instagram_organizer.infrastructure.ai.gemini_client import GeminiClient
from instagram_organizer.infrastructure.filesystem.output_router import OutputRouter
from instagram_organizer.infrastructure.filesystem.post_exporter import PostExporter
from instagram_organizer.infrastructure.filesystem.workspace_manager import WorkspaceManager
from instagram_organizer.infrastructure.instagram.instaloader_client import InstaloaderClient
from instagram_organizer.infrastructure.instagram.session_manager import SessionManager
from instagram_organizer.infrastructure.persistence.jsonl_tracker_repository import JsonlTrackerRepository
from instagram_organizer.infrastructure.persistence.run_state_repository import RunStateJsonRepository


def build_runtime(settings: AppSettings) -> ApplicationRuntime:
    """Construct the concrete application runtime from settings."""

    logger = logging.getLogger('instagram_organizer')
    instagram_client = InstaloaderClient()
    session_store = SessionManager(settings.ig_session_file)
    ai_service = AIAnalysisService(
        analyzer=GeminiClient(
            api_key=settings.gemini_api_key,
            model_name=settings.gemini_model,
            inline_max_bytes=settings.gemini_inline_max_bytes,
            use_files_api=settings.gemini_use_files_api,
            use_batch_fallback=settings.gemini_use_batch_fallback,
        )
    )
    primary_tracker = TrackerService(JsonlTrackerRepository(settings.primary_tracker_file))
    duplicate_tracker = TrackerService(JsonlTrackerRepository(settings.duplicate_tracker_file))
    output_router = OutputRouter(
        organized_dir=settings.organized_dir,
        manual_dir=settings.manual_dir,
        duplicates_dir=settings.duplicates_dir,
    )
    run_state_repository = RunStateJsonRepository(settings.run_state_file)
    recovery_service = RecoveryService(
        repository=run_state_repository,
        output_router=output_router,
    )
    post_processor = PostProcessor(
        instagram_client=instagram_client,
        analysis_service=ai_service,
        duplicate_service=DuplicateService(),
        run_state_repository=run_state_repository,
        workspace_manager=WorkspaceManager(settings.workspace_dir),
        output_router=output_router,
        post_exporter=PostExporter(),
        routing_policy=OutputRoutingPolicy(),
        base_dir=settings.base_dir,
        max_ai_images=settings.max_ai_images,
    )
    duplicate_service = post_processor.duplicate_service
    return ApplicationRuntime(
        instagram_client=instagram_client,
        session_store=session_store,
        ai_analysis_service=ai_service,
        primary_tracker=primary_tracker,
        duplicate_tracker=duplicate_tracker,
        duplicate_service=duplicate_service,
        recovery_service=recovery_service,
        post_processor=post_processor,
        index_service=IndexService(
            primary_text_path=settings.primary_index_file,
            duplicate_text_path=settings.duplicate_index_file,
        ),
        logger=logger,
    )


def build_orchestrator(settings: AppSettings) -> Orchestrator:
    """Construct the main application orchestrator."""

    runtime = build_runtime(settings)
    return Orchestrator(settings=settings, runtime=runtime, logger=runtime.logger)


def build_auth_service(settings: AppSettings) -> AuthService:
    """Construct the authentication service used by CLI auth commands."""

    runtime = build_runtime(settings)
    assert runtime.session_store is not None
    return AuthService(
        instagram_client=runtime.instagram_client,
        session_store=runtime.session_store,
    )


def build_maintenance_service(settings: AppSettings) -> MaintenanceService:
    """Construct the maintenance service used by non-run CLI commands."""

    primary_tracker = TrackerService(JsonlTrackerRepository(settings.primary_tracker_file))
    duplicate_tracker = TrackerService(JsonlTrackerRepository(settings.duplicate_tracker_file))
    index_service = IndexService(
        primary_text_path=settings.primary_index_file,
        duplicate_text_path=settings.duplicate_index_file,
    )
    run_state_repository = RunStateJsonRepository(settings.run_state_file)
    return MaintenanceService(
        primary_tracker=primary_tracker,
        duplicate_tracker=duplicate_tracker,
        index_service=index_service,
        run_state_repository=run_state_repository,
    )


def dispatch(args: Namespace, settings: AppSettings) -> int:
    """Execute the resolved CLI command.

    Args:
        args: Parsed command-line arguments.
        settings: Resolved application settings.

    Returns:
        Process exit code.
    """

    command = getattr(args, 'command', 'run') or 'run'
    if command == 'run':
        return build_orchestrator(settings).run()
    if command == 'login':
        return _login(settings)
    if command == 'session-status':
        return _session_status(settings, json_output=bool(getattr(args, 'json', False)))
    if command == 'logout':
        return _logout(settings)
    if command == 'validate-config':
        return _validate_config(settings, json_output=bool(getattr(args, 'json', False)))
    if command == 'show-settings':
        return _show_settings(settings)
    if command == 'show-run-state':
        return _show_run_state(settings, json_output=bool(getattr(args, 'json', False)))
    if command == 'clear-run-state':
        return _clear_run_state(settings)
    if command == 'rebuild-indexes':
        return _rebuild_indexes(settings)
    raise ValueError(f'Unsupported command: {command}')


def _login(settings: AppSettings) -> int:
    try:
        message = build_auth_service(settings).login_with_optional_two_factor(settings.ig_username)
    except Exception as exc:
        print(f'Login failed: {exc}')
        return 1
    print(message)
    return 0


def _session_status(settings: AppSettings, *, json_output: bool) -> int:
    status = build_auth_service(settings).session_status(settings.ig_username)
    payload = status.to_dict()
    if json_output:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Configured Instagram username: {status.username or '(not set)'}")
        print(f"Session file: {status.session_file}")
        print(f"Exists: {status.exists}")
        if status.exists:
            print(f"Size (bytes): {status.size_bytes}")
            print(f"Modified (UTC): {status.modified_at_utc}")
    return 0


def _logout(settings: AppSettings) -> int:
    removed = build_auth_service(settings).logout()
    if removed:
        print('Saved Instagram session removed.')
    else:
        print('No saved Instagram session file was present.')
    return 0


def _validate_config(settings: AppSettings, *, json_output: bool) -> int:
    report = validate_settings(settings)
    if json_output:
        print(
            json.dumps(
                {
                    'valid': report.is_valid,
                    'errors': [issue.__dict__ for issue in report.errors],
                    'warnings': [issue.__dict__ for issue in report.warnings],
                },
                indent=2,
            )
        )
    else:
        status = 'valid' if report.is_valid else 'invalid'
        print(f'Configuration status: {status}')
        for issue in report.errors:
            print(f"ERROR [{issue.field_name}] {issue.message}")
        for issue in report.warnings:
            print(f"WARNING [{issue.field_name}] {issue.message}")
        if report.is_valid and not report.warnings:
            print('No validation issues detected.')
    return 0 if report.is_valid else 1


def _show_settings(settings: AppSettings) -> int:
    print(json.dumps(settings.to_redacted_dict(), indent=2))
    return 0


def _show_run_state(settings: AppSettings, *, json_output: bool) -> int:
    state = build_maintenance_service(settings).load_run_state()
    if state is None:
        print('{}' if json_output else 'No saved run state.')
        return 0

    payload: dict[str, Any] = state.to_dict()
    if json_output:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Interrupted shortcode: {state.shortcode}")
        print(f"Step: {state.step.value}")
        print(f"Workspace: {payload.get('workspace_path')}")
        print(f"Partial output: {payload.get('partial_output_path')}")
        print(f"Progress: {payload.get('post_index')} / {payload.get('total_posts')}")
    return 0


def _clear_run_state(settings: AppSettings) -> int:
    existed = build_maintenance_service(settings).clear_run_state()
    if existed:
        print('Saved run state cleared.')
    else:
        print('No saved run state to clear.')
    return 0


def _rebuild_indexes(settings: AppSettings) -> int:
    primary_count, duplicate_count = build_maintenance_service(settings).rebuild_indexes()
    print(
        'Rebuilt indexes from tracker data: '
        f'{primary_count} primary record(s), {duplicate_count} duplicate record(s).'
    )
    return 0
