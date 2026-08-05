"""
Provider interfaces (contracts). Concrete implementations arrive in Phase 2.

Defining the interfaces now keeps every provider swappable behind one boundary,
which is the whole point of the model-agnostic design.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class TextProvider(ABC):
    """Contract for text generation (headlines + descriptions)."""

    @abstractmethod
    def generate(self, prompt: str, *, max_tokens: int = 1024) -> str:
        """Return generated text for the given prompt."""
        raise NotImplementedError


class ImageProvider(ABC):
    """Contract for branded image generation."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        reference_images: list[str] | None = None,
    ) -> bytes:
        """Return generated image bytes for the given prompt and references."""
        raise NotImplementedError
