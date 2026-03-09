from pathlib import Path

from PIL import Image

from instagram_organizer.infrastructure.ai.files_api import GeminiFilesApiClient
from instagram_organizer.infrastructure.ai.gemini_client import GeminiClient
from instagram_organizer.infrastructure.ai.payloads import build_inline_batches


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeModel:
    def __init__(self, responses: list[str] | None = None) -> None:
        self.calls = []
        self._responses = list(
            responses
            or [
                '{"per_image_analysis":["one"],"ocr_summary":"ocr","dominant_signal":"visual",'
                '"combined_analysis":"combo","title":"Example Title"}'
            ]
        )

    def generate_content(self, content, generation_config=None):
        self.calls.append((content, generation_config))
        response_text = self._responses.pop(0)
        return FakeResponse(response_text)


class RaisingFilesApiClient(GeminiFilesApiClient):
    def upload_paths(self, image_paths):
        raise RuntimeError('upload failed')


class TrackingFilesApiClient(GeminiFilesApiClient):
    def __init__(self) -> None:
        self.uploaded = []
        self.deleted = []

    def upload_paths(self, image_paths):
        self.uploaded = list(image_paths)
        return type('Uploaded', (), {'items': ['file-1', 'file-2']})()

    def delete_uploaded_files(self, uploaded):
        self.deleted = list(uploaded.items)


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


def test_gemini_client_uses_files_api_when_inline_payload_is_too_large(tmp_path: Path) -> None:
    huge_path = tmp_path / 'huge.jpg'
    huge_path.write_bytes(b'x' * 128)
    fake_model = FakeModel()
    tracking_files = TrackingFilesApiClient()
    client = GeminiClient(
        api_key='key',
        model_factory=lambda _: fake_model,
        configure_fn=lambda api_key: None,
        inline_max_bytes=32,
        use_files_api=True,
        use_batch_fallback=False,
        files_api_client=tracking_files,
    )

    result = client.analyze([huge_path], caption='')
    assert result.title == 'Example Title'
    assert tracking_files.uploaded == [huge_path]
    assert tracking_files.deleted == ['file-1', 'file-2']
    assert fake_model.calls[0][0][1:] == ['file-1', 'file-2']



def test_gemini_client_falls_back_to_batch_synthesis_when_files_api_fails(tmp_path: Path) -> None:
    image_one = tmp_path / 'one.jpg'
    image_two = tmp_path / 'two.jpg'
    Image.new('RGB', (10, 10), color='red').save(image_one)
    Image.new('RGB', (10, 10), color='blue').save(image_two)

    fake_model = FakeModel(
        responses=[
            '{"per_image_analysis":["batch1"],"ocr_summary":"ocr1","dominant_signal":"visual",'
            '"combined_analysis":"combo1","title":"Batch One"}',
            '{"per_image_analysis":["batch2"],"ocr_summary":"ocr2","dominant_signal":"text",'
            '"combined_analysis":"combo2","title":"Batch Two"}',
            '{"per_image_analysis":["full1","full2"],"ocr_summary":"ocr full","dominant_signal":"balanced",'
            '"combined_analysis":"merged","title":"Whole Post Final Title"}',
        ]
    )

    client = GeminiClient(
        api_key='key',
        model_factory=lambda _: fake_model,
        configure_fn=lambda api_key: None,
        inline_max_bytes=120,
        use_files_api=True,
        use_batch_fallback=True,
        files_api_client=RaisingFilesApiClient(),
    )

    result = client.analyze([image_one, image_two], caption='caption')
    assert result.title == 'Whole Post Final Title'
    assert len(fake_model.calls) == 3
    assert len(fake_model.calls[2][0]) == 1
    assert 'Batch analyses JSON' in fake_model.calls[2][0][0]



def test_build_inline_batches_preserves_order(tmp_path: Path) -> None:
    first = tmp_path / 'first.bin'
    second = tmp_path / 'second.bin'
    third = tmp_path / 'third.bin'
    first.write_bytes(b'a' * 50)
    second.write_bytes(b'b' * 50)
    third.write_bytes(b'c' * 50)

    plan = build_inline_batches(
        [first, second, third],
        prompt_text='prompt',
        max_inline_bytes=110,
    )

    assert plan.batch_count == 2
    assert plan.batches[0] == (first, second)
    assert plan.batches[1] == (third,)
