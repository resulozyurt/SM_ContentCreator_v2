"""
Claude text provider (Anthropic API).

Used for headline + description generation. The model id comes from config
(CLAUDE_TEXT_MODEL), never hardcoded, so upgrading models is a config change.
"""

from __future__ import annotations

from app.config import get_settings
from app.providers.base import ProviderError, TextProvider


class ClaudeTextProvider(TextProvider):
    """Text generation backed by Anthropic's Messages API."""

    name = "claude"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.anthropic_api_key
        self._model = model or settings.claude_text_model
        if not self._api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not set. See .env.example.")
        # Imported lazily so the package need not be installed unless this
        # provider is actually used.
        from anthropic import Anthropic

        self._client = Anthropic(api_key=self._api_key)

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 1.0,
    ) -> str:
        try:
            kwargs: dict = {
                "model": self._model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                kwargs["system"] = system
            response = self._client.messages.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 - surface a uniform error type
            raise ProviderError(f"Claude request failed: {exc}") from exc

        # Concatenate all text blocks in the response.
        parts = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ]
        text = "".join(parts).strip()
        if not text:
            raise ProviderError("Claude returned an empty response.")
        return text
