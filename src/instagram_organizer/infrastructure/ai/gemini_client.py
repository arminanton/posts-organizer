"""Gemini-backed title-analysis adapter.

The class in this module is the concrete infrastructure implementation of the
``TitleAnalyzer`` protocol. The adapter isolates API-specific prompt building,
transport strategy, image preparation, and structured-response parsing from the
rest of the application.
"""

from __future__ import annotations

import json
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

from PIL import Image

from instagram_organizer.domain.exceptions import AnalysisError
from instagram_organizer.domain.models import AIAnalysis
from instagram_organizer.domain.protocols import TitleAnalyzer
from instagram_organizer.infrastructure.ai.files_api import GeminiFilesApiClient
from instagram_organizer.infrastructure.ai.payloads import PayloadPlan, build_inline_batches
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
        inline_max_bytes: Safe upper bound for inline image requests.
        use_files_api: Whether large payloads may switch to the Gemini Files API.
        use_batch_fallback: Whether to split large payloads into multiple inline
            requests when the Files API path fails.
        files_api_client: Optional override for uploaded-file transport.
    """

    api_key: str
    model_name: str = "gemini-1.5-flash"
    parser: ResponseParser = parse_analysis_payload
    model_factory: ModelFactory | None = None
    configure_fn: ConfigureFn | None = None
    inline_max_bytes: int = 18_000_000
    use_files_api: bool = True
    use_batch_fallback: bool = True
    files_api_client: GeminiFilesApiClient | None = None
    _model: Any | None = field(default=None, init=False, repr=False)

    def analyze(self, image_paths: Sequence[Path], caption: str = "") -> AIAnalysis:
        """Analyze images and return structured AI output.

        The adapter prefers a single inline request. When the estimated inline
        payload is too large, it attempts the Files API. If that fails and batch
        fallback is enabled, the adapter analyzes ordered image batches and then
        synthesizes them into one final whole-post result.
        """

        if not image_paths:
            raise AnalysisError("Gemini analysis requires at least one image")

        prompt = self._build_prompt(caption=caption)
        plan = build_inline_batches(
            image_paths,
            prompt_text=prompt,
            max_inline_bytes=self.inline_max_bytes,
        )

        if plan.batch_count == 1 and plan.estimated_bytes <= self.inline_max_bytes:
            return self._analyze_inline(image_paths=image_paths, prompt=prompt)

        last_error: Exception | None = None
        if self.use_files_api:
            try:
                return self._analyze_via_files_api(image_paths=image_paths, prompt=prompt)
            except Exception as exc:  # pragma: no cover - defensive path
                last_error = exc

        if self.use_batch_fallback:
            try:
                return self._analyze_in_batches(
                    image_paths=image_paths,
                    caption=caption,
                    plan=plan,
                )
            except Exception as exc:  # pragma: no cover - defensive path
                if last_error is None:
                    last_error = exc
                else:
                    wrapped = AnalysisError(
                        "Gemini Files API failed and batch fallback also failed"
                    )
                    wrapped.__cause__ = exc
                    last_error = wrapped

        if last_error is not None:
            raise AnalysisError("Gemini analysis strategy failed") from last_error
        raise AnalysisError("Gemini analysis could not choose a transport strategy")

    def _analyze_inline(self, *, image_paths: Sequence[Path], prompt: str) -> AIAnalysis:
        model = self._get_model()
        with ExitStack() as stack:
            images = [self._prepare_image(stack, path) for path in image_paths]
            response = model.generate_content(
                [prompt, *images],
                generation_config=self._generation_config(),
            )
        return self.parser(getattr(response, "text", "") or "")

    def _analyze_via_files_api(
        self,
        *,
        image_paths: Sequence[Path],
        prompt: str,
    ) -> AIAnalysis:
        model = self._get_model()
        files_api = self.files_api_client or GeminiFilesApiClient()
        uploaded = files_api.upload_paths(image_paths)
        try:
            response = model.generate_content(
                [prompt, *uploaded.items],
                generation_config=self._generation_config(),
            )
        finally:
            files_api.delete_uploaded_files(uploaded)
        return self.parser(getattr(response, "text", "") or "")

    def _analyze_in_batches(
        self,
        *,
        image_paths: Sequence[Path],
        caption: str,
        plan: PayloadPlan | None = None,
    ) -> AIAnalysis:
        prompt = self._build_prompt(caption=caption)
        if plan is None:
            plan = build_inline_batches(
                image_paths,
                prompt_text=prompt,
                max_inline_bytes=self.inline_max_bytes,
            )

        analyses: list[AIAnalysis] = []
        for batch in plan.batches:
            analyses.append(self._analyze_inline(image_paths=batch, prompt=prompt))

        if len(analyses) == 1:
            return analyses[0]
        return self._synthesize_batch_analyses(analyses=analyses, caption=caption)

    def _synthesize_batch_analyses(
        self,
        *,
        analyses: Sequence[AIAnalysis],
        caption: str,
    ) -> AIAnalysis:
        model = self._get_model()
        payload = [analysis.to_dict() for analysis in analyses]
        synthesis_prompt = self._build_batch_synthesis_prompt(
            batch_payload=payload,
            caption=caption,
        )
        response = model.generate_content(
            [synthesis_prompt],
            generation_config=self._generation_config(),
        )
        return self.parser(getattr(response, "text", "") or "")

    def _build_batch_synthesis_prompt(
        self,
        *,
        batch_payload: Sequence[dict[str, object]],
        caption: str,
    ) -> str:
        caption = caption.strip()
        caption_block = ""
        if caption:
            caption_block = (
                "\n\nOptional caption context:\n"
                f"{caption}\n"
                "Use caption only as secondary context after visual synthesis."
            )

        return (
            "You are given structured analyses from multiple ordered batches that "
            "belong to the same Instagram post. Combine them into one whole-post "
            "analysis. Preserve the overall meaning of the full carousel, not just "
            "one batch. Return valid JSON with keys: per_image_analysis, "
            "ocr_summary, dominant_signal, combined_analysis, and title. The title "
            "must be 6 to 10 words using only standard English letters and numbers. "
            "Use MANUAL_REVIEW when the full post remains too vague."
            f"{caption_block}\n\nBatch analyses JSON:\n"
            f"{json.dumps(batch_payload, ensure_ascii=False)}"
        )

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
