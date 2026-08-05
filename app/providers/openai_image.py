"""
OpenAI image provider (gpt-image family) — FALLBACK.

Used when the primary (Gemini) provider fails, and for A/B comparison. Model id
from config (OPENAI_IMAGE_MODEL, default gpt-image-1). When reference images are
supplied it uses the image-edit endpoint; otherwise plain generation.
"""

from __future__ import annotations

import base64
import io

from app.config import get_settings
from app.providers.base import ImageProvider, ProviderError, ReferenceImage


class OpenAIImageProvider(ImageProvider):
    """Branded image generation backed by OpenAI's images API."""

    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        size: str = "1024x1024",
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.openai_api_key
        self._model = model or settings.openai_image_model
        self._size = size
        if not self._api_key:
            raise ProviderError("OPENAI_API_KEY is not set. See .env.example.")
        from openai import OpenAI

        self._client = OpenAI(api_key=self._api_key)

    def generate(
        self,
        prompt: str,
        *,
        reference_images: list[ReferenceImage] | None = None,
    ) -> bytes:
        try:
            if reference_images:
                files = [
                    (f"ref_{i}.png", io.BytesIO(ref.data), ref.mime_type)
                    for i, ref in enumerate(reference_images)
                ]
                result = self._client.images.edit(
                    model=self._model,
                    image=files,
                    prompt=prompt,
                    size=self._size,
                )
            else:
                result = self._client.images.generate(
                    model=self._model,
                    prompt=prompt,
                    size=self._size,
                )
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"OpenAI image request failed: {exc}") from exc

        data = getattr(result, "data", None) or []
        if not data:
            raise ProviderError("OpenAI returned no image data.")
        b64 = getattr(data[0], "b64_json", None)
        if not b64:
            raise ProviderError("OpenAI response missing b64_json image payload.")
        return base64.b64decode(b64)
