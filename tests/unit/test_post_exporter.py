import json
import lzma
from datetime import datetime, timezone
from pathlib import Path

from instagram_organizer.domain.enums import DominantSignal, MediaType
from instagram_organizer.domain.models import AIAnalysis
from instagram_organizer.infrastructure.filesystem.post_exporter import PostExporter


class FakePost:
    shortcode = 'abc123'
    caption = 'caption #tag'
    likes = 7
    comments = 2
    date_utc = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)


def test_post_exporter_moves_files_and_writes_sidecars(tmp_path: Path) -> None:
    workspace = tmp_path / 'workspace'
    destination = tmp_path / 'out'
    workspace.mkdir()
    destination.mkdir()
    (workspace / 'slide1.jpg').write_bytes(b'img')
    with lzma.open(workspace / 'meta.json.xz', 'wt', encoding='utf-8') as handle:
        json.dump({'ok': True}, handle)

    analysis = AIAnalysis(
        title='Example Title',
        dominant_signal=DominantSignal.VISUAL,
        per_image_analysis=('one',),
        ocr_summary='ocr',
        combined_analysis='combo',
        raw_payload={'title': 'Example Title'},
    )

    exporter = PostExporter()
    exporter.export_workspace(workspace, destination)
    exporter.write_sidecars(
        destination=destination,
        post=FakePost(),
        analysis=analysis,
        media_type=MediaType.IMAGE,
        hashtags=('#tag',),
        engagement_rate=9.0,
    )

    assert (destination / 'slide1.jpg').exists()
    assert json.loads((destination / 'metadata' / 'meta.json').read_text(encoding='utf-8')) == {'ok': True}
    assert 'Example Title' in (destination / 'ai_analysis.txt').read_text(encoding='utf-8')
    assert (destination / 'ai_analysis.json').exists()
