from datetime import datetime, timezone
from pathlib import Path

from instagram_organizer.application.ai_analysis_service import AIAnalysisService
from instagram_organizer.application.duplicate_service import DuplicateService
from instagram_organizer.application.post_processor import PostProcessor
from instagram_organizer.domain.enums import OutputCategory
from instagram_organizer.domain.models import AIAnalysis
from instagram_organizer.domain.services import OutputRoutingPolicy
from instagram_organizer.infrastructure.filesystem.output_router import OutputRouter
from instagram_organizer.infrastructure.filesystem.post_exporter import PostExporter
from instagram_organizer.infrastructure.filesystem.workspace_manager import WorkspaceManager
from instagram_organizer.infrastructure.persistence.run_state_repository import RunStateJsonRepository


class FakeAnalyzer:
    def analyze(self, image_paths, caption: str = '') -> AIAnalysis:
        return AIAnalysis(title='Complex Topic Overview')


class FakeInstagramClient:
    loader = object()

    def download_post(self, post, workspace: Path) -> None:
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / 'slide1.jpg').write_bytes(b'img')


class FakePost:
    shortcode = 'abc123'
    caption = 'caption #alpha #beta'
    likes = 10
    comments = 5
    is_video = False
    typename = 'GraphImage'
    date_utc = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)


def test_post_processor_creates_processed_record(tmp_path: Path) -> None:
    processor = PostProcessor(
        instagram_client=FakeInstagramClient(),
        analysis_service=AIAnalysisService(FakeAnalyzer()),
        duplicate_service=DuplicateService(),
        run_state_repository=RunStateJsonRepository(tmp_path / 'run_state.json'),
        workspace_manager=WorkspaceManager(tmp_path / 'workspaces'),
        output_router=OutputRouter(tmp_path / 'organized', tmp_path / 'manual', tmp_path / 'duplicates'),
        post_exporter=PostExporter(),
        routing_policy=OutputRoutingPolicy(),
        base_dir=tmp_path,
        max_ai_images=10,
    )

    record = processor.process(
        post=FakePost(),
        total_followers=100,
        post_index=1,
        total_posts=1,
    )

    assert record.shortcode == 'abc123'
    assert record.output_category is OutputCategory.ORGANIZED
    assert (tmp_path / record.folder).exists()
    assert processor.run_state_repository.load() is None
