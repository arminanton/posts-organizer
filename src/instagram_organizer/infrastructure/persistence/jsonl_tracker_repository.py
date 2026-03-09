"""JSONL-backed repository for processed-post records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from instagram_organizer.domain.exceptions import PersistenceError
from instagram_organizer.domain.models import ProcessedPost
from instagram_organizer.infrastructure.persistence.atomic_writer import atomic_write_text


@dataclass(slots=True)
class JsonlTrackerRepository:
    """Persist processed-post records in newline-delimited JSON.

    The repository de-duplicates records by shortcode when loading or rewriting.
    Appends are kept simple and durable using flush plus fsync.
    """

    path: Path

    def load_records(self) -> list[ProcessedPost]:
        """Load unique processed-post records sorted by timestamp."""

        if not self.path.exists():
            return []

        by_shortcode: dict[str, ProcessedPost] = {}
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    raw = line.strip()
                    if not raw:
                        continue
                    try:
                        data = json.loads(raw)
                        record = ProcessedPost.from_dict(data)
                    except Exception as exc:
                        raise PersistenceError(
                            f"Malformed tracker line {line_number} in {self.path}"
                        ) from exc
                    by_shortcode[record.shortcode] = record
        except OSError as exc:
            raise PersistenceError(f"Failed to read tracker file: {self.path}") from exc

        return sorted(by_shortcode.values(), key=lambda item: item.timestamp)

    def append(self, record: ProcessedPost) -> None:
        """Append one processed-post record durably to the JSONL file."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
                handle.flush()
                import os
                os.fsync(handle.fileno())
        except OSError as exc:
            raise PersistenceError(f"Failed to append tracker record: {self.path}") from exc

    def rewrite(self, records: list[ProcessedPost]) -> None:
        """Rewrite the tracker canonically using one record per shortcode."""

        deduped: dict[str, ProcessedPost] = {record.shortcode: record for record in records}
        ordered = sorted(deduped.values(), key=lambda item: item.timestamp)
        content = "".join(
            json.dumps(record.to_dict(), ensure_ascii=False) + "\n"
            for record in ordered
        )
        atomic_write_text(self.path, content)
