"""Workspace lifecycle management for per-post processing."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class WorkspaceManager:
    """Create, reuse, and clean up per-post local workspaces.

    Args:
        base_dir: Parent directory under which workspaces are created.

    Example:
        >>> manager = WorkspaceManager(base_dir=Path("tmp"))
        >>> manager.workspace_for("abc123").name
        'post_abc123'
    """

    base_dir: Path

    def workspace_for(self, shortcode: str) -> Path:
        """Return the stable workspace path for one post shortcode."""

        return self.base_dir / f"post_{shortcode}"

    def prepare(self, shortcode: str, *, reuse_existing: bool = True) -> Path:
        """Create or reuse a stable per-post workspace.

        Args:
            shortcode: Instagram shortcode for the post.
            reuse_existing: Whether to keep existing files when the directory
                already exists.

        Returns:
            The workspace path ready for use.
        """

        self.base_dir.mkdir(parents=True, exist_ok=True)
        workspace = self.workspace_for(shortcode)
        if workspace.exists() and not reuse_existing:
            shutil.rmtree(workspace)
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def cleanup(self, workspace: Path) -> None:
        """Delete a workspace directory if it exists."""

        if workspace.exists():
            shutil.rmtree(workspace)
