"""
Provider factory — the single place callers get an AI provider from.

Callers never import concrete providers directly; they call get_text_provider()
or get_image_provider(). Swapping a model or provider is a config/one-file change
here, which is the whole point of the model-agnostic design.
"""

from __future__ import annotations

import logging

from app.providers.base import ImageProvider, ProviderError, ReferenceImage, TextProvider

logger = logging.getLogger(__name__)


def get_text_provider() -> TextProvider:
    """Return the configured text provider (currently Claude)."""
    from app.providers.claude import ClaudeTextProvider

    return ClaudeTextProvider()


class FallbackImageProvider(ImageProvider):
    """
    Wraps a primary and a fallback image provider.

    Tries the primary first; on ProviderError, logs and retries with the
    fallback. Raises only if both fail.
    """

    name = "image_fallback"

    def __init__(self, primary: ImageProvider, fallback: ImageProvider) -> None:
        self._primary = primary
        self._fallback = fallback

    def generate(
        self,
        prompt: str,
        *,
        reference_images: list[ReferenceImage] | None = None,
    ) -> bytes:
        try:
            return self._primary.generate(prompt, reference_images=reference_images)
        except ProviderError as exc:
            logger.warning(
                "Primary image provider '%s' failed (%s); falling back to '%s'.",
                self._primary.name,
                exc,
                self._fallback.name,
            )
            return self._fallback.generate(prompt, reference_images=reference_images)


def get_image_provider(*, with_fallback: bool = True) -> ImageProvider:
    """
    Return the configured image provider.

    Primary is Gemini; if with_fallback, wrap it so OpenAI takes over on failure.
    """
    from app.providers.gemini import GeminiImageProvider
    from app.providers.openai_image import OpenAIImageProvider

    primary = GeminiImageProvider()
    if not with_fallback:
        return primary
    return FallbackImageProvider(primary=primary, fallback=OpenAIImageProvider())
