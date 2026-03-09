from pathlib import Path

from instagram_organizer.application.ai_analysis_service import AIAnalysisService
from instagram_organizer.application.duplicate_service import DuplicateService
from instagram_organizer.application.index_service import IndexService
from instagram_organizer.application.orchestrator import Orchestrator
from instagram_organizer.application.post_processor import PostProcessor
from instagram_organizer.application.recovery_service import RecoveryService
from instagram_organizer.application.runtime import ApplicationRuntime
from instagram_organizer.application.tracker_service import TrackerService
from instagram_organizer.config.settings import AppSettings, LoggingSettings
from instagram_organizer.domain.models import AIAnalysis
from instagram_organizer.domain.services import OutputRoutingPolicy
from instagram_organizer.infrastructure.filesystem.output_router import OutputRouter
from instagram_organizer.infrastructure.filesystem.post_exporter import PostExporter
from instagram_organizer.infrastructure.filesystem.workspace_manager import WorkspaceManager
from instagram_organizer.infrastructure.persistence.jsonl_tracker_repository import JsonlTrackerRepository
from instagram_organizer.infrastructure.persistence.run_state_repository import RunStateJsonRepository


class FakeInstagramClient:
    def __init__(self) -> None:
        self.loader = object()

    def fetch_profile(self, username: str):
        return type('Profile', (), {
            'mediacount': 1,
            'followers': 100,
            'get_posts': lambda self: [type('Post', (), {
                'shortcode': 'abc123',
                'caption': 'caption #tag',
                'likes': 5,
                'comments': 1,
                'is_video': False,
                'typename': 'GraphImage',
                'date_utc': __import__('datetime').datetime(2026, 3, 8, 10, 0, tzinfo=__import__('datetime').timezone.utc),
            })()],
        })()

    def iter_posts(self, profile):
        return profile.get_posts()

    def download_post(self, post, workspace: Path) -> None:
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / 'slide1.jpg').write_bytes(b'img')


class FakeAnalyzer:
    def analyze(self, image_paths, caption: str = '') -> AIAnalysis:
        return AIAnalysis(title='Example Title')


class FakeSessionStore:
    def load(self, loader, username: str) -> None:
        return None

    def save(self, loader) -> None:
        return None


def test_orchestrator_runs_smoke(tmp_path: Path) -> None:
    settings = AppSettings(
        gemini_api_key='key',
        gemini_model='gemini-1.5-flash',
        target_account='target',
        base_dir=tmp_path,
        results_root=tmp_path / 'results',
        ig_username=None,
        ig_session_file=tmp_path / 'results' / 'state' / '.ig_session',
        max_ai_images=10,
        gemini_inline_max_bytes=18_000_000,
        gemini_use_files_api=True,
        gemini_use_batch_fallback=True,
        logging=LoggingSettings(
            app_log_file=tmp_path / 'results' / 'logs' / 'app.log',
            error_log_file=tmp_path / 'results' / 'logs' / 'error.log',
        ),
    )
    output_router = OutputRouter(settings.organized_dir, settings.manual_dir, settings.duplicates_dir)
    runtime = ApplicationRuntime(
        instagram_client=FakeInstagramClient(),
        session_store=FakeSessionStore(),
        ai_analysis_service=AIAnalysisService(FakeAnalyzer()),
        primary_tracker=TrackerService(JsonlTrackerRepository(settings.primary_tracker_file)),
        duplicate_tracker=TrackerService(JsonlTrackerRepository(settings.duplicate_tracker_file)),
        duplicate_service=DuplicateService(),
        recovery_service=RecoveryService(RunStateJsonRepository(settings.run_state_file), output_router),
        post_processor=PostProcessor(
            instagram_client=FakeInstagramClient(),
            analysis_service=AIAnalysisService(FakeAnalyzer()),
            duplicate_service=DuplicateService(),
            run_state_repository=RunStateJsonRepository(settings.run_state_file),
            workspace_manager=WorkspaceManager(settings.workspace_dir),
            output_router=output_router,
            post_exporter=PostExporter(),
            routing_policy=OutputRoutingPolicy(),
            base_dir=settings.base_dir,
            max_ai_images=settings.max_ai_images,
        ),
        index_service=IndexService(settings.primary_index_file, settings.duplicate_index_file),
        logger=__import__('logging').getLogger('test'),
    )
    runtime.post_processor.duplicate_service = runtime.duplicate_service
    orchestrator = Orchestrator(settings=settings, runtime=runtime, logger=runtime.logger)
    assert orchestrator.run() == 0
    assert settings.primary_tracker_file.exists()
    assert settings.primary_index_file.exists()
