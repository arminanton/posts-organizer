"""Retry-related helpers."""

from __future__ import annotations

import random


def exponential_backoff(attempt: int, base: float, maximum: float) -> float:
    """Return exponential backoff with small random jitter."""

    raw = min(base * (2 ** max(0, attempt - 1)), maximum)
    return raw + random.uniform(0.0, 2.0)
