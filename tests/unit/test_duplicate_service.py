from instagram_organizer.application.duplicate_service import DuplicateService
from instagram_organizer.domain.enums import MediaType
from instagram_organizer.domain.models import ProcessedPost


def test_duplicate_service_detects_previously_seen_title() -> None:
    service = DuplicateService()
    service.seed(
        [
            ProcessedPost(
                shortcode="abc",
                title="Title",
                normalized_title="title",
                media_type=MediaType.IMAGE,
                date="2026-03-08",
                time="10:00:00 UTC",
                engagement="1.23%",
                hashtags="",
                timestamp=1.0,
                folder="Organized_Posts/Title",
            )
        ]
    )

    assert service.is_duplicate("title") is True
    assert service.is_duplicate("other") is False
