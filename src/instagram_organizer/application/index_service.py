"""Write human-readable and JSON index files from tracker state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from instagram_organizer.domain.models import ProcessedPost
from instagram_organizer.infrastructure.persistence.atomic_writer import atomic_write_json, atomic_write_text


@dataclass(slots=True)
class IndexService:
    """Persist summary index files for processed posts."""

    primary_text_path: Path
    duplicate_text_path: Path

    def write(self, primary_records: Sequence[ProcessedPost], duplicate_records: Sequence[ProcessedPost]) -> None:
        """Write both human-readable and JSON indexes for current tracker state."""

        atomic_write_text(
            self.primary_text_path,
            self._render_text_index('MASTER POST INDEX', primary_records),
        )
        atomic_write_json(
            self.primary_text_path.with_suffix('.json'),
            [record.to_dict() for record in sorted(primary_records, key=lambda item: item.timestamp)],
        )

        if duplicate_records:
            atomic_write_text(
                self.duplicate_text_path,
                self._render_text_index('MASTER DUPLICATES INDEX', duplicate_records),
            )
            atomic_write_json(
                self.duplicate_text_path.with_suffix('.json'),
                [record.to_dict() for record in sorted(duplicate_records, key=lambda item: item.timestamp)],
            )
            return

        if self.duplicate_text_path.exists():
            self.duplicate_text_path.unlink()
        duplicate_json = self.duplicate_text_path.with_suffix('.json')
        if duplicate_json.exists():
            duplicate_json.unlink()

    def _render_text_index(self, title: str, records: Sequence[ProcessedPost]) -> str:
        lines = [f"=== {title} ===\n"]
        for record in sorted(records, key=lambda item: item.timestamp):
            tags = f" | {record.hashtags}" if record.hashtags else ''
            lines.append(
                f"- {record.title} | {record.date} | {record.time} | "
                f"{record.engagement} | {record.media_type.value}{tags} | {record.folder}\n"
            )
        return ''.join(lines)
