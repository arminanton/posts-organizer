from __future__ import annotations

from instagram_organizer.config.settings import AppSettings
from instagram_organizer.domain.models import ProcessedPost


def test_sample_settings_fixture(sample_settings: AppSettings):
    assert sample_settings.base_dir.name == "project"
    assert sample_settings.target_account == "target-account"


def test_sample_record_fixture(sample_record: ProcessedPost):
    assert sample_record.shortcode == "ABC123"
    assert sample_record.media_type.value == "image"
