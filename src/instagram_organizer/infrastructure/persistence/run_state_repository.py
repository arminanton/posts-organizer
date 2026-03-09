"""Run-state persistence adapter."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from instagram_organizer.domain.exceptions import PersistenceError
from instagram_organizer.domain.models import RunState
from instagram_organizer.infrastructure.persistence.atomic_writer import atomic_write_json


@dataclass(slots=True)
class RunStateJsonRepository:
    """Persist recovery state as JSON in one file."""

    path: Path

    def load(self) -> RunState | None:
        """Load the saved run state, if any."""

        if not self.path.exists():
            return None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return RunState.from_dict(data)
        except OSError as exc:
            raise PersistenceError(f"Failed to read run-state file: {self.path}") from exc
        except Exception as exc:
            raise PersistenceError(f"Run-state file is invalid: {self.path}") from exc

    def save(self, state: RunState) -> None:
        """Persist the current run-state snapshot."""

        try:
            atomic_write_json(self.path, state.to_dict())
        except Exception as exc:
            raise PersistenceError(f"Failed to save run-state file: {self.path}") from exc

    def clear(self) -> None:
        """Delete the saved run-state file if present."""

        try:
            if self.path.exists():
                self.path.unlink()
        except OSError as exc:
            raise PersistenceError(f"Failed to clear run-state file: {self.path}") from exc
