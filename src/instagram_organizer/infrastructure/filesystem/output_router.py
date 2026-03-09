"""Filesystem routing for processed-post output folders."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from instagram_organizer.domain.enums import OutputCategory
from instagram_organizer.domain.services import sanitize_title_for_filesystem


@dataclass(slots=True)
class OutputRouter:
    """Resolve and reserve destination folders for processed posts."""

    organized_dir: Path
    manual_dir: Path
    duplicates_dir: Path

    def base_directory(self, category: OutputCategory) -> Path:
        """Return the base directory for the given output category."""

        if category is OutputCategory.MANUAL_REVIEW:
            return self.manual_dir
        if category is OutputCategory.DUPLICATE:
            return self.duplicates_dir
        return self.organized_dir

    def reserve_destination(
        self,
        *,
        category: OutputCategory,
        post_date: str,
        title: str,
        shortcode: str,
    ) -> Path:
        """Create and return a unique destination directory for one post.

        Manual-review folders include the shortcode for easier human recovery,
        while organized folders prioritize the date and sanitized title.
        """

        base = self.base_directory(category)
        base.mkdir(parents=True, exist_ok=True)
        safe_title = sanitize_title_for_filesystem(title)

        if category is OutputCategory.MANUAL_REVIEW:
            folder_name = f"{post_date}_{safe_title}_{shortcode}"
        elif category is OutputCategory.DUPLICATE:
            folder_name = f"{safe_title}_{post_date}_{shortcode}"
        else:
            folder_name = f"{post_date}_{safe_title}"

        path = base / folder_name
        counter = 1
        while path.exists():
            path = base / f"{folder_name}_{counter}"
            counter += 1

        path.mkdir(parents=True, exist_ok=False)
        return path

    def cleanup_partial(self, path: Path | None) -> None:
        """Remove a partially written output directory if it exists."""

        if path and path.exists():
            shutil.rmtree(path)
