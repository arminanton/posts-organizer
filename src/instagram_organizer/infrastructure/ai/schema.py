"""Schema helpers for Gemini structured output.

This module centralizes the JSON schema used for model responses so the AI
adapter and tests stay consistent. Keeping the schema in one place also makes
future migrations to another provider easier.
"""

from __future__ import annotations


def analysis_response_schema() -> dict[str, object]:
    """Return the JSON schema for AI analysis responses.

    Returns:
        A JSON-schema-compatible dictionary describing the expected payload.

    Example:
        >>> schema = analysis_response_schema()
        >>> schema["type"]
        'object'
    """

    return {
        "type": "object",
        "properties": {
            "per_image_analysis": {
                "type": "array",
                "items": {"type": "string"},
            },
            "ocr_summary": {"type": "string"},
            "dominant_signal": {
                "type": "string",
                "enum": ["visual", "text", "balanced", "uncertain"],
            },
            "combined_analysis": {"type": "string"},
            "title": {"type": "string"},
        },
        "required": [
            "per_image_analysis",
            "ocr_summary",
            "dominant_signal",
            "combined_analysis",
            "title",
        ],
        "additionalProperties": True,
    }
