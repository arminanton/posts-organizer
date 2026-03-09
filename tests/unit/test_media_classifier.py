from dataclasses import dataclass

from instagram_organizer.domain.enums import MediaType
from instagram_organizer.infrastructure.instagram.media_classifier import (
    classify_from_flags,
    classify_post,
)


@dataclass
class FakeNode:
    is_video: bool


class FakePost:
    def __init__(self, *, is_video: bool = False, typename: str = '', nodes=None) -> None:
        self.is_video = is_video
        self.typename = typename
        self._nodes = nodes or []

    def get_sidecar_nodes(self):
        return list(self._nodes)


def test_classify_from_flags_detects_mixed() -> None:
    assert classify_from_flags(is_video=False, has_video=True, has_image=True) is MediaType.MIXED


def test_classify_post_detects_sidecar_images() -> None:
    post = FakePost(typename='GraphSidecar', nodes=[FakeNode(False), FakeNode(False)])
    assert classify_post(post) is MediaType.IMAGE


def test_classify_post_detects_video() -> None:
    post = FakePost(is_video=True)
    assert classify_post(post) is MediaType.VIDEO
