import json
import lzma
from pathlib import Path

from instagram_organizer.infrastructure.filesystem.metadata_extractor import (
    read_compressed_json,
    scan_workspace,
)


def test_scan_workspace_categorizes_files(tmp_path: Path) -> None:
    (tmp_path / 'a.jpg').write_bytes(b'x')
    (tmp_path / 'b.mp4').write_bytes(b'x')
    (tmp_path / 'c.txt').write_text('x', encoding='utf-8')
    media = scan_workspace(tmp_path)
    assert [path.name for path in media.image_files] == ['a.jpg']
    assert [path.name for path in media.video_files] == ['b.mp4']


def test_read_compressed_json_decodes_payload(tmp_path: Path) -> None:
    path = tmp_path / 'meta.json.xz'
    with lzma.open(path, 'wt', encoding='utf-8') as handle:
        json.dump({'a': 1}, handle)
    assert read_compressed_json(path) == {'a': 1}
