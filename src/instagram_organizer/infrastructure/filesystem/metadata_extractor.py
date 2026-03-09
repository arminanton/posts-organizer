"""Helpers for downloaded media and metadata files."""

from __future__ import annotations

import json
import lzma
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from instagram_organizer.domain.exceptions import PersistenceError

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
_VIDEO_SUFFIXES = {".mp4"}


@dataclass(frozen=True, slots=True)
class DownloadedMedia:
    """Classify files discovered inside a post workspace."""

    all_files: tuple[Path, ...]
    image_files: tuple[Path, ...]
    video_files: tuple[Path, ...]


def scan_workspace(workspace: Path) -> DownloadedMedia:
    """Return categorized media files found inside a workspace directory."""

    files = tuple(sorted(path for path in workspace.iterdir() if path.is_file()))
    image_files = tuple(path for path in files if path.suffix.lower() in _IMAGE_SUFFIXES)
    video_files = tuple(path for path in files if path.suffix.lower() in _VIDEO_SUFFIXES)
    return DownloadedMedia(files, image_files, video_files)


def read_compressed_json(path: Path) -> dict[str, Any]:
    """Read one Instaloader ``.json.xz`` file into a parsed object."""

    try:
        with lzma.open(path, "rt", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, lzma.LZMAError, json.JSONDecodeError) as exc:
        raise PersistenceError(f"Failed to read compressed metadata: {path}") from exc

    if not isinstance(data, dict):
        raise PersistenceError(f"Compressed metadata did not decode to an object: {path}")
    return data
