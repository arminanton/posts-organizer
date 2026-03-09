"""Time and sleep helpers."""

from __future__ import annotations

import time


def utc_timestamp_string() -> str:
    """Return the current UTC timestamp in a human-readable format."""

    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
