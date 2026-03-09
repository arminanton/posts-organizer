from instagram_organizer.domain.exceptions import AnalysisError
from instagram_organizer.infrastructure.ai.response_parser import (
    extract_json_object,
    parse_analysis_payload,
    parse_json_object,
    strip_markdown_fences,
)


def test_strip_markdown_fences_removes_json_block() -> None:
    raw = """```json
{"title":"Example"}
```"""
    assert strip_markdown_fences(raw) == '{"title":"Example"}'


def test_extract_json_object_handles_extra_prose() -> None:
    raw = """Here you go
```json
{"title":"Example"}
```
Thanks"""
    assert extract_json_object(raw) == '{"title":"Example"}'


def test_parse_analysis_payload_reads_title() -> None:
    payload = (
        '{"per_image_analysis":["one"],"ocr_summary":"text","dominant_signal":"visual",'
        '"combined_analysis":"combo","title":"Example Title"}'
    )
    result = parse_analysis_payload(payload)
    assert result.title == "Example Title"
    assert result.ocr_summary == "text"


def test_parse_json_object_raises_on_missing_json() -> None:
    try:
        parse_json_object("no json here")
    except AnalysisError:
        assert True
    else:
        assert False
