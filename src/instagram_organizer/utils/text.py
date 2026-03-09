"""Text-sanitization helpers."""

from __future__ import annotations

import re
import unicodedata


def sanitize_filename(name: str, max_len: int = 80) -> str:
    """Sanitize a string for filesystem-friendly use."""

    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9 _-]", "", normalized)
    cleaned = re.sub(r"\s+", "_", cleaned).strip("._-")
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned[:max_len] or "UNTITLED"
