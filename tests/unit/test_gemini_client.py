from pathlib import Path

from PIL import Image

from instagram_organizer.infrastructure.ai.gemini_client import GeminiClient


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeModel:
    def __init__(self) -> None:
        self.calls = []

    def generate_content(self, content, generation_config=None):
        self.calls.append((content, generation_config))
        return FakeResponse(
            '{"per_image_analysis":["one"],"ocr_summary":"ocr","dominant_signal":"visual",'
            '"combined_analysis":"combo","title":"Example Title"}'
        )


def test_gemini_client_returns_analysis(tmp_path: Path) -> None:
    image_path = tmp_path / 'image.png'
    Image.new('RGBA', (4, 4), color=(255, 0, 0, 128)).save(image_path)

    fake_model = FakeModel()
    client = GeminiClient(
        api_key='key',
        model_factory=lambda _: fake_model,
        configure_fn=lambda api_key: None,
    )
    result = client.analyze([image_path], caption='caption')
    assert result.title == 'Example Title'
    sent_prompt = fake_model.calls[0][0][0]
    assert 'caption' in sent_prompt
