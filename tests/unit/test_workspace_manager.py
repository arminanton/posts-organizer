from pathlib import Path

from instagram_organizer.infrastructure.filesystem.workspace_manager import WorkspaceManager


def test_workspace_manager_creates_stable_directory(tmp_path: Path) -> None:
    manager = WorkspaceManager(base_dir=tmp_path / 'tmp')
    workspace = manager.prepare('abc123')
    assert workspace.exists()
    assert workspace.name == 'post_abc123'


def test_workspace_manager_can_reset_directory(tmp_path: Path) -> None:
    manager = WorkspaceManager(base_dir=tmp_path / 'tmp')
    workspace = manager.prepare('abc123')
    (workspace / 'stale.txt').write_text('x', encoding='utf-8')
    workspace = manager.prepare('abc123', reuse_existing=False)
    assert not (workspace / 'stale.txt').exists()
