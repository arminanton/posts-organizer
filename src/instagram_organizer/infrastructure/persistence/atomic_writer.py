"""Atomic file-writing utilities.

These helpers ensure that callers either observe the full new file contents or
keep the old file intact. Unique sibling temp files avoid corruption when two
processes write near the same time.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from instagram_organizer.domain.exceptions import PersistenceError


def atomic_write_text(path: Path, content: str) -> None:
    """Atomically replace a text file using a unique sibling temp file.

    Args:
        path: Final target path.
        content: Full text content to write.

    Raises:
        PersistenceError: If the file cannot be written safely.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f"{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_name = handle.name
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except OSError as exc:
        if temp_name:
            try:
                Path(temp_name).unlink(missing_ok=True)
            except OSError:
                pass
        raise PersistenceError(f"Failed to atomically write file: {path}") from exc


def atomic_write_json(path: Path, payload: Any) -> None:
    """Serialize a JSON-compatible value and write it atomically."""

    atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
