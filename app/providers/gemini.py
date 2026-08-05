"""
Gemini image provider (Google Gen AI) — PRIMARY.

Uses Gemini "Nano Banana Pro" (model id from config, default gemini-3-pro-image)
because it can render high-fidelity, multilingual text inside images and hold
brand consistency across reference images.

NOTE: the exact behavior of the preview image model is confirmed against the
live API via scripts/smoke_providers.py (run with a real GOOGLE_API_KEY). The
extraction below reads inline image bytes from the response parts, which is the
standard shape for Gemini image-output models.
"""

from __future__ import annotations

from app.config import get_settings
from app.providers.base import ImageProvider, ProviderError, ReferenceImage


class GeminiImageProvider(ImageProvider):
    """Branded image generation backed by Google Gen AI image models."""

    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.google_api_key
        self._model = model or settings.gemini_image_model
        if not self._api_key:
            raise ProviderError("GOOGLE_API_KEY is not set. See .env.example.")
        from google import genai

        self._genai = genai
        self._client = genai.Client(api_key=self._api_key)

    def generate(
        self,
        prompt: str,
        *,
        reference_images: list[ReferenceImage] | None = None,
    ) -> bytes:
        from google.genai import types

        contents: list = [prompt]
        for ref in reference_images or []:
            contents.append(
                types.Part.from_bytes(data=ref.data, mime_type=ref.mime_type)
            )

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=contents,
            )
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"Gemini request failed: {exc}") from exc

        image_bytes = self._extract_image(response)
        if image_bytes is None:
            raise ProviderError("Gemini returned no image data.")
        return image_bytes

    @staticmethod
    def _extract_image(response) -> bytes | None:
        """Pull the first inline image payload out of a generate_content response."""
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                inline = getattr(part, "inline_data", None)
                if inline is not None and getattr(inline, "data", None):
                    return inline.data
        return None
