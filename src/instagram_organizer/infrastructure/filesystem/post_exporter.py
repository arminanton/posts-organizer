"""Move downloaded workspace content into the final output structure."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from instagram_organizer.domain.enums import MediaType
from instagram_organizer.domain.models import AIAnalysis
from instagram_organizer.infrastructure.filesystem.metadata_extractor import read_compressed_json
from instagram_organizer.infrastructure.persistence.atomic_writer import (
    atomic_write_json,
    atomic_write_text,
)


@dataclass(slots=True)
class PostExporter:
    """Persist one processed post into its final destination folder.

    The exporter is intentionally focused on filesystem concerns only. It moves
    downloaded media, normalizes Instaloader metadata, and writes lightweight
    sidecar files that make the output easy to inspect later.
    """

    def export_workspace(self, workspace: Path, destination: Path) -> None:
        """Move all workspace files into the destination folder.

        Instaloader ``.json.xz`` metadata files are unpacked into a dedicated
        ``metadata`` directory as plain JSON for easier inspection and reuse.
        """

        metadata_dir = destination / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)

        for source_path in sorted(workspace.iterdir()):
            if not source_path.is_file():
                continue
            if source_path.name.endswith(".json.xz"):
                target_path = metadata_dir / source_path.name[:-3]
                payload = read_compressed_json(source_path)
                atomic_write_json(target_path, payload)
                source_path.unlink(missing_ok=True)
                continue
            shutil.move(str(source_path), str(destination / source_path.name))

    def write_sidecars(
        self,
        *,
        destination: Path,
        post: Any,
        analysis: AIAnalysis,
        media_type: MediaType,
        hashtags: tuple[str, ...],
        engagement_rate: float,
    ) -> None:
        """Write text and JSON sidecar files for one processed post."""

        if hashtags:
            atomic_write_text(destination / "hashtags.txt", ", ".join(hashtags) + "\n")

        engagement_text = "\n".join(
            [
                "=== ENGAGEMENT METRICS ===",
                f"Likes: {int(getattr(post, 'likes', 0) or 0)}",
                f"Comments: {int(getattr(post, 'comments', 0) or 0)}",
                f"Engagement Rate: {engagement_rate:.2f}%",
                "",
            ]
        )
        atomic_write_text(destination / "engagement.txt", engagement_text)

        caption = str(getattr(post, "caption", "") or "")
        notes = [
            "=== POST DETAILS ===",
            f"Shortcode: {str(getattr(post, 'shortcode', ''))}",
            f"Media Type: {media_type.value}",
            f"Date UTC: {str(getattr(post, 'date_utc', ''))}",
            "",
            "=== CAPTION ===",
            caption or "No caption",
            "",
            "=== AI TITLE ===",
            analysis.title,
        ]
        atomic_write_text(destination / "notes.txt", "\n".join(notes) + "\n")

        if analysis.raw_payload:
            atomic_write_json(destination / "ai_analysis.json", analysis.raw_payload)

        rendered = self.render_analysis_text(analysis)
        if rendered:
            atomic_write_text(destination / "ai_analysis.txt", rendered + "\n")

    def render_analysis_text(self, analysis: AIAnalysis) -> str:
        """Render a structured AI analysis as a readable text report."""

        parts: list[str] = []
        if analysis.per_image_analysis:
            parts.append("=== PER IMAGE ANALYSIS ===")
            for index, item in enumerate(analysis.per_image_analysis, start=1):
                parts.extend(["", f"Image {index}:", item])

        if analysis.ocr_summary:
            parts.extend(["", "=== OCR SUMMARY ===", analysis.ocr_summary])
        parts.extend(["", "=== DOMINANT SIGNAL ===", analysis.dominant_signal.value])
        if analysis.combined_analysis:
            parts.extend(["", "=== COMBINED ANALYSIS ===", analysis.combined_analysis])
        parts.extend(["", "=== FINAL TITLE ===", analysis.title])
        return "\n".join(parts).strip()
