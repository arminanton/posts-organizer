from __future__ import annotations

from pathlib import Path


DOC_FILES = [
    "architecture.md",
    "testing.md",
    "operations.md",
    "recovery.md",
]


def test_docs_exist(project_root: Path | None = None):
    root = Path(__file__).resolve().parents[2]
    docs = root / "docs"
    for name in DOC_FILES:
        assert (docs / name).exists(), name
