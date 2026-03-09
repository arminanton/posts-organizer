import json
from pathlib import Path

from instagram_organizer.infrastructure.persistence.atomic_writer import (
    atomic_write_json,
    atomic_write_text,
)


def test_atomic_write_text_replaces_file(tmp_path: Path) -> None:
    path = tmp_path / 'data.txt'
    atomic_write_text(path, 'hello')
    atomic_write_text(path, 'world')
    assert path.read_text(encoding='utf-8') == 'world'


def test_atomic_write_json_serializes_payload(tmp_path: Path) -> None:
    path = tmp_path / 'data.json'
    atomic_write_json(path, {'a': 1})
    assert json.loads(path.read_text(encoding='utf-8')) == {'a': 1}
