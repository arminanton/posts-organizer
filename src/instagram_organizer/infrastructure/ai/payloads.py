"""Helpers for Gemini payload planning.

This module keeps byte-estimation and batching rules separate from the Gemini
adapter so the transport strategy remains testable and easier to evolve.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True, slots=True)
class PayloadPlan:
    """Plan describing how inline image payload should be partitioned.

    Args:
        estimated_bytes: Estimated total payload size in bytes.
        batches: Ordered image batches that remain within the configured limit.
    """

    estimated_bytes: int
    batches: tuple[tuple[Path, ...], ...]

    @property
    def batch_count(self) -> int:
        """Return the number of planned batches."""

        return len(self.batches)


def estimate_inline_payload_bytes(
    image_paths: Sequence[Path],
    *,
    prompt_text: str,
) -> int:
    """Estimate inline Gemini request size using source file sizes.

    The Google SDK handles serialization internally, so this estimate is based
    on the current on-disk image sizes plus encoded prompt size. The estimate is
    intentionally conservative enough to support a safety margin in settings.
    """

    total = len(prompt_text.encode('utf-8'))
    for path in image_paths:
        total += path.stat().st_size
    return total


def build_inline_batches(
    image_paths: Sequence[Path],
    *,
    prompt_text: str,
    max_inline_bytes: int,
) -> PayloadPlan:
    """Split images into ordered inline batches under a byte threshold.

    Args:
        image_paths: Ordered source images.
        prompt_text: Prompt text that contributes to each inline request.
        max_inline_bytes: Safe ceiling for each inline request.

    Returns:
        A payload plan with one or more ordered batches.
    """

    if max_inline_bytes <= 0:
        raise ValueError('max_inline_bytes must be positive')

    base_bytes = len(prompt_text.encode('utf-8'))
    estimated = estimate_inline_payload_bytes(image_paths, prompt_text=prompt_text)

    batches: list[list[Path]] = []
    current: list[Path] = []
    current_bytes = base_bytes

    for path in image_paths:
        path_bytes = path.stat().st_size
        if current and current_bytes + path_bytes > max_inline_bytes:
            batches.append(current)
            current = [path]
            current_bytes = base_bytes + path_bytes
        else:
            current.append(path)
            current_bytes += path_bytes

    if current:
        batches.append(current)

    return PayloadPlan(
        estimated_bytes=estimated,
        batches=tuple(tuple(batch) for batch in batches),
    )
