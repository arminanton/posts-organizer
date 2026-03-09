"""Gemini-backed title-analysis adapter.

The class in this module is the concrete infrastructure implementation of the
``TitleAnalyzer`` protocol. The adapter isolates API-specific prompt building,
image preparation, and structured-response parsing from the rest of the
application.
"""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

from PIL import Image

from instagram_organizer.domain.exceptions import AnalysisError
from instagram_organizer.domain.models import AIAnalysis
from instagram_organizer.domain.protocols import TitleAnalyzer
from instagram_organizer.infrastructure.ai.response_parser import parse_analysis_payload
from instagram_organizer.infrastructure.ai.schema import analysis_response_schema

ResponseParser = Callable[[str], AIAnalysis]
ModelFactory = Callable[[str], Any]
ConfigureFn = Callable[[str], None]


@dataclass(slots=True)
class GeminiClient(TitleAnalyzer):
    """Analyze post images with Gemini structured output.

    Args:
        api_key: Gemini API key.
        model_name: Gemini model identifier.
        parser: Function used to turn raw model text into ``AIAnalysis``.
        model_factory: Optional override used by tests to inject a fake model.
        configure_fn: Optional override used by tests to inject fake config.

    Example:
        >>> client = GeminiClient(api_key="key", model_factory=lambda _: object())
        >>> client.model_name
        'gemini-1.5-flash'
    """

    api_key: str
    model_name: str = "gemini-1.5-flash"
    parser: ResponseParser = parse_analysis_payload
    model_factory: ModelFactory | None = None
    configure_fn: ConfigureFn | None = None
    _model: Any | None = field(default=None, init=False, repr=False)

    def analyze(self, image_paths: Sequence[Path], caption: str = "") -> AIAnalysis:
        """Analyze images and return structured AI output.

        Args:
            image_paths: Ordered image paths belonging to one Instagram post.
            caption: Optional caption text to pass as secondary context.

        Returns:
            Structured AI analysis for the whole post.

        Raises:
            AnalysisError: If no images are provided or the API response fails.
        """

        if not image_paths:
            raise AnalysisError("Gemini analysis requires at least one image")

        prompt = self._build_prompt(caption=caption)
        model = self._get_model()

        with ExitStack() as stack:
            images = [self._prepare_image(stack, path) for path in image_paths]
            response = model.generate_content(
                [prompt, *images],
                generation_config=self._generation_config(),
            )

        response_text = getattr(response, "text", "") or ""
        return self.parser(response_text)

    def _get_model(self) -> Any:
        """Create the Gemini model lazily so tests can inject fakes."""

        if self._model is not None:
            return self._model

        configure = self.configure_fn
        factory = self.model_factory
        if configure is None or factory is None:
            try:
                import google.generativeai as genai  # type: ignore
            except ImportError as exc:
                raise AnalysisError(
                    "google-generativeai is required to use GeminiClient"
                ) from exc
            configure = configure or (lambda api_key: genai.configure(api_key=api_key))
            factory = factory or genai.GenerativeModel

        configure(self.api_key)
        self._model = factory(self.model_name)
        return self._model

    def _generation_config(self) -> Any:
        """Return generation config with JSON schema for structured output."""

        try:
            import google.generativeai as genai  # type: ignore
        except ImportError:
            return {
                "response_mime_type": "application/json",
                "response_schema": analysis_response_schema(),
            }

        return genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=analysis_response_schema(),
        )

    def _prepare_image(self, stack: ExitStack, path: Path) -> Image.Image:
        """Open one image and normalize its mode without resizing.

        The image is copied into RGB mode to avoid serialization issues from
        palette or alpha-based sources while preserving original dimensions.
        """

        source = stack.enter_context(Image.open(path))
        return source.convert("RGB")

    def _build_prompt(self, caption: str = "") -> str:
        """Build the structured prompt for Gemini analysis."""

        caption = caption.strip()
        caption_block = ""
        if caption:
            caption_block = (
                "\n\nOptional caption context:\n"
                f"{caption}\n"
                "Use caption only as secondary context after visual analysis."
            )

        return (
            "Analyze the provided images from a single educational Instagram post.\n\n"
            "Study all images together in order. Give priority to visual meaning, then "
            "use OCR text as secondary context when relevant. If a slide is mostly text, "
            "you may allow the text signal to dominate.\n\n"
            "Return valid JSON with keys: per_image_analysis, ocr_summary, "
            "dominant_signal, combined_analysis, and title. The title must be 6 to 10 "
            "words using only standard English letters and numbers. Use MANUAL_REVIEW "
            "when the content is too vague."
            f"{caption_block}"
        )
