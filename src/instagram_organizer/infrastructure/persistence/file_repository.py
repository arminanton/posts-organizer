"""Filesystem persistence helper placeholders."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class FileRepository:
    """Minimal filesystem helper wrapper."""

    base_dir: Path

    def ensure(self, relative_path: str) -> Path:
        """Create and return a child path under the repository base directory."""

        path = self.base_dir / relative_path
        path.mkdir(parents=True, exist_ok=True)
        return path
