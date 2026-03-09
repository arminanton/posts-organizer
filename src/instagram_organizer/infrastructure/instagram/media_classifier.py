"""Instagram media-classification helpers."""

from __future__ import annotations

from typing import Any

from instagram_organizer.domain.enums import MediaType


def classify_from_flags(*, is_video: bool, has_video: bool, has_image: bool) -> MediaType:
    """Classify media type from normalized boolean flags."""

    if is_video:
        return MediaType.VIDEO
    if has_video and has_image:
        return MediaType.MIXED
    if has_video:
        return MediaType.VIDEO
    if has_image:
        return MediaType.IMAGE
    return MediaType.UNKNOWN


def classify_post(post: Any) -> MediaType:
    """Classify a post-like object based on Instaloader-style attributes.

    The function only depends on the small attribute subset used by the real
    script, which makes it easy to test with simple fakes.
    """

    if bool(getattr(post, "is_video", False)):
        return MediaType.VIDEO

    if getattr(post, "typename", "") == "GraphSidecar":
        nodes = list(getattr(post, "get_sidecar_nodes")())
        has_video = any(bool(getattr(node, "is_video", False)) for node in nodes)
        has_image = any(not bool(getattr(node, "is_video", False)) for node in nodes)
        return classify_from_flags(is_video=False, has_video=has_video, has_image=has_image)

    return MediaType.IMAGE
