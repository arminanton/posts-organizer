"""Parse and sanitize AI structured-output responses.

Gemini and similar models can still occasionally return JSON wrapped in
Markdown fences or extra explanatory text. This parser extracts the first JSON
object defensively before handing the payload to the domain model.
"""

from __future__ import annotations

import json
import re
from typing import Any

from instagram_organizer.domain.exceptions import AnalysisError
from instagram_organizer.domain.models import AIAnalysis


_FENCE_PREFIX = re.compile(r"^```(?:json)?\s*", flags=re.IGNORECASE)
_FENCE_SUFFIX = re.compile(r"\s*```$", flags=re.IGNORECASE)


def strip_markdown_fences(raw_text: str) -> str:
    """Remove common Markdown code fences around JSON payloads.

    Args:
        raw_text: Raw model output that may include fenced JSON.

    Returns:
        Cleaned text with leading and trailing code fences removed.
    """

    text = raw_text.strip()
    text = _FENCE_PREFIX.sub("", text)
    text = _FENCE_SUFFIX.sub("", text)
    return text.strip()


def extract_json_object(raw_text: str) -> str:
    """Extract the first complete JSON object from arbitrary text.

    Args:
        raw_text: Raw model output that may include prose around the payload.

    Returns:
        The substring containing the first balanced JSON object.

    Raises:
        AnalysisError: If no balanced JSON object can be found.
    """

    cleaned = strip_markdown_fences(raw_text)
    start = cleaned.find("{")
    if start == -1:
        raise AnalysisError("AI response did not contain a JSON object")

    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(cleaned[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return cleaned[start : index + 1]

    raise AnalysisError("AI response contained an incomplete JSON object")


def parse_json_object(raw_text: str) -> dict[str, Any]:
    """Parse a raw model response into a JSON object.

    Args:
        raw_text: Raw text returned by the AI model.

    Returns:
        Parsed JSON object.

    Raises:
        AnalysisError: If the payload cannot be decoded into a JSON object.
    """

    try:
        data = json.loads(extract_json_object(raw_text))
    except json.JSONDecodeError as exc:
        raise AnalysisError("AI response was not valid JSON") from exc

    if not isinstance(data, dict):
        raise AnalysisError("Expected AI response to decode into a JSON object")
    return data


def parse_analysis_payload(raw_text: str) -> AIAnalysis:
    """Parse raw model output into a typed ``AIAnalysis`` value object.

    Args:
        raw_text: Raw text emitted by the AI model.

    Returns:
        Typed analysis model created from the parsed JSON object.
    """

    return AIAnalysis.from_dict(parse_json_object(raw_text))
