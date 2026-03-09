"""Hashing and stable-key helpers."""

from __future__ import annotations

import hashlib


def stable_sha1(value: str) -> str:
    """Return a stable SHA-1 hex digest for the provided value."""

    return hashlib.sha1(value.encode("utf-8")).hexdigest()
