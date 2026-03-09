"""Single-post processing use case."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
from pathlib import Path
from typing import Any

from instagram_organizer.application.ai_analysis_service import AIAnalysisService
from instagram_organizer.application.duplicate_service import DuplicateService
from instagram_organizer.domain.enums import MediaType, OutputCategory, ProcessingStep
from instagram_organizer.domain.models import AIAnalysis, ProcessedPost, RunState
from instagram_organizer.domain.protocols import InstagramClient, RunStateRepository
from instagram_organizer.domain.services import OutputRoutingPolicy, extract_hashtags
from instagram_organizer.infrastructure.filesystem.metadata_extractor import scan_workspace
from instagram_organizer.infrastructure.filesystem.output_router import OutputRouter
from instagram_organizer.infrastructure.filesystem.post_exporter import PostExporter
from instagram_organizer.infrastructure.filesystem.workspace_manager import WorkspaceManager
from instagram_organizer.infrastructure.instagram.media_classifier import classify_post


@dataclass(slots=True)
class PostProcessor:
    """Process one Instagram post end to end.

    The processor coordinates download, AI analysis, routing, filesystem export,
    and run-state checkpoints for a single post. It is intentionally isolated
    from feed iteration so it can be unit-tested with simple fakes.
    """

    instagram_client: InstagramClient
    analysis_service: AIAnalysisService
    duplicate_service: DuplicateService
    run_state_repository: RunStateRepository
    workspace_manager: WorkspaceManager
    output_router: OutputRouter
    post_exporter: PostExporter
    routing_policy: OutputRoutingPolicy
    base_dir: Path
    max_ai_images: int = 10

    def process(
        self,
        *,
        post: Any,
        total_followers: int,
        post_index: int,
        total_posts: int,
        reuse_workspace: bool = False,
    ) -> ProcessedPost:
        """Process one post and return its persistent tracker record."""

        shortcode = str(getattr(post, 'shortcode'))
        workspace = self.workspace_manager.prepare(shortcode, reuse_existing=reuse_workspace)
        self.run_state_repository.save(
            RunState(
                shortcode=shortcode,
                step=ProcessingStep.STARTING,
                workspace_path=workspace,
                post_index=post_index,
                total_posts=total_posts,
            )
        )

        self.run_state_repository.save(
            RunState(
                shortcode=shortcode,
                step=ProcessingStep.DOWNLOADING,
                workspace_path=workspace,
                post_index=post_index,
                total_posts=total_posts,
            )
        )
        self.instagram_client.download_post(post, workspace)

        media = scan_workspace(workspace)
        media_type = classify_post(post)

        self.run_state_repository.save(
            RunState(
                shortcode=shortcode,
                step=ProcessingStep.ANALYZING,
                workspace_path=workspace,
                post_index=post_index,
                total_posts=total_posts,
            )
        )
        analysis = self._analysis_for_post(post=post, media_type=media_type, image_paths=media.image_files)

        decision = self.routing_policy.decide(
            title=analysis.title,
            normalized_title=analysis.normalized_title,
            seen_titles=self.duplicate_service.seen_titles,
        )
        destination = self.output_router.reserve_destination(
            category=decision.category,
            post_date=self._date_string(post),
            title=analysis.title,
            shortcode=shortcode,
        )

        self.run_state_repository.save(
            RunState(
                shortcode=shortcode,
                step=ProcessingStep.WRITING_FILES,
                workspace_path=workspace,
                partial_output_path=destination,
                post_index=post_index,
                total_posts=total_posts,
            )
        )
        self.post_exporter.export_workspace(workspace, destination)

        hashtags = extract_hashtags(getattr(post, 'caption', None))
        engagement_rate = self._engagement_rate(post=post, total_followers=total_followers)
        self.post_exporter.write_sidecars(
            destination=destination,
            post=post,
            analysis=analysis,
            media_type=media_type,
            hashtags=hashtags,
            engagement_rate=engagement_rate,
        )

        record = ProcessedPost(
            shortcode=shortcode,
            title=analysis.title,
            normalized_title=analysis.normalized_title,
            media_type=media_type,
            date=self._date_string(post),
            time=self._time_string(post),
            engagement=f"{engagement_rate:.2f}%",
            hashtags=', '.join(hashtags),
            timestamp=self._timestamp(post),
            folder=str(destination.relative_to(self.base_dir)),
            output_category=decision.category,
        )

        self.run_state_repository.save(
            RunState(
                shortcode=shortcode,
                step=ProcessingStep.COMPLETED,
                workspace_path=workspace,
                partial_output_path=destination,
                post_index=post_index,
                total_posts=total_posts,
            )
        )
        self.workspace_manager.cleanup(workspace)
        self.run_state_repository.clear()
        return record

    def _analysis_for_post(
        self,
        *,
        post: Any,
        media_type: MediaType,
        image_paths: tuple[Path, ...],
    ) -> AIAnalysis:
        if media_type is MediaType.VIDEO:
            return AIAnalysis(title='VIDEO_POST')
        if media_type in {MediaType.IMAGE, MediaType.MIXED} and image_paths:
            return self.analysis_service.analyze(
                image_paths=image_paths[: self.max_ai_images],
                caption=str(getattr(post, 'caption', '') or ''),
            )
        return AIAnalysis(title='MANUAL_REVIEW')

    def _engagement_rate(self, *, post: Any, total_followers: int) -> float:
        likes = int(getattr(post, 'likes', 0) or 0)
        comments = int(getattr(post, 'comments', 0) or 0)
        if total_followers <= 0:
            return 0.0
        return ((likes + comments) / total_followers) * 100.0

    def _timestamp(self, post: Any) -> float:
        date_utc = getattr(post, 'date_utc')
        return float(date_utc.timestamp())

    def _date_string(self, post: Any) -> str:
        date_utc = getattr(post, 'date_utc')
        return date_utc.astimezone(timezone.utc).strftime('%Y-%m-%d')

    def _time_string(self, post: Any) -> str:
        date_utc = getattr(post, 'date_utc')
        return date_utc.astimezone(timezone.utc).strftime('%H:%M:%S UTC')
