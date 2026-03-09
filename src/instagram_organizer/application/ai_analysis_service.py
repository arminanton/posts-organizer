"""Application-facing wrapper around title analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from instagram_organizer.domain.models import AIAnalysis
from instagram_organizer.domain.protocols import TitleAnalyzer


@dataclass(slots=True)
class AIAnalysisService:
    """Coordinate requests to the configured title analyzer."""

    analyzer: TitleAnalyzer

    def analyze(self, image_paths: Sequence[Path], caption: str = "") -> AIAnalysis:
        """Delegate image analysis to the analyzer implementation."""

        return self.analyzer.analyze(image_paths=image_paths, caption=caption)
