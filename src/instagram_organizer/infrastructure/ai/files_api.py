"""Lightweight helpers around the Gemini Files API.

The project prefers inline image parts when possible, but can switch to the
Files API for larger requests. This helper isolates upload and cleanup behavior
from the main Gemini adapter.
"""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from instagram_organizer.domain.exceptions import AnalysisError

UploadFn = Callable[..., Any]
DeleteFn = Callable[..., Any]


@dataclass(slots=True)
class UploadedFiles:
    """Container for uploaded Gemini file references."""

    items: list[Any]


class GeminiFilesApiClient:
    """Best-effort adapter around ``google.generativeai`` file helpers."""

    def __init__(
        self,
        *,
        upload_fn: UploadFn | None = None,
        delete_fn: DeleteFn | None = None,
        module_getter: Callable[[], Any] | None = None,
    ) -> None:
        self._upload_fn = upload_fn
        self._delete_fn = delete_fn
        self._module_getter = module_getter

    def upload_paths(self, image_paths: Sequence[Path]) -> UploadedFiles:
        """Upload one or more paths through the configured Files API client."""

        uploaded: list[Any] = []
        for path in image_paths:
            uploaded.append(self._upload_one(path))
        return UploadedFiles(items=uploaded)

    def delete_uploaded_files(self, uploaded: UploadedFiles) -> None:
        """Delete uploaded file handles best-effort and ignore cleanup errors."""

        delete_fn = self._resolve_delete_fn()
        if delete_fn is None:
            return

        for item in uploaded.items:
            identifier = getattr(item, 'name', None) or getattr(item, 'uri', None) or item
            try:
                delete_fn(identifier)
            except TypeError:
                try:
                    delete_fn(name=identifier)
                except Exception:
                    continue
            except Exception:
                continue

    def _upload_one(self, path: Path) -> Any:
        upload_fn = self._resolve_upload_fn()
        mime_type, _ = mimetypes.guess_type(path.name)
        try:
            return upload_fn(path=str(path), mime_type=mime_type)
        except TypeError:
            try:
                return upload_fn(str(path), mime_type=mime_type)
            except TypeError:
                return upload_fn(str(path))
        except Exception as exc:
            raise AnalysisError(f'Gemini Files API upload failed for {path.name}') from exc

    def _resolve_upload_fn(self) -> UploadFn:
        if self._upload_fn is not None:
            return self._upload_fn
        module = self._resolve_module()
        upload_fn = getattr(module, 'upload_file', None)
        if upload_fn is None:
            raise AnalysisError('Gemini Files API upload_file is unavailable')
        return upload_fn

    def _resolve_delete_fn(self) -> DeleteFn | None:
        if self._delete_fn is not None:
            return self._delete_fn
        module = self._resolve_module()
        return getattr(module, 'delete_file', None)

    def _resolve_module(self) -> Any:
        if self._module_getter is None:
            try:
                import google.generativeai as genai  # type: ignore
            except ImportError as exc:
                raise AnalysisError(
                    'google-generativeai is required for Files API support'
                ) from exc
            return genai
        return self._module_getter()
