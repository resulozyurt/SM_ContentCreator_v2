"""
Provider interfaces (contracts) for the model-agnostic AI layer.

Every provider sits behind one of these two interfaces. Swapping or upgrading a
model touches exactly one implementation file; callers depend only on these
abstractions and on the factory (see factory.py).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderError(RuntimeError):
    """Raised when a provider call fails (network, auth, bad response, etc.)."""


@dataclass
class ReferenceImage:
    """An input reference image for brand-consistent generation."""

    data: bytes
    mime_type: str = "image/png"


class TextProvider(ABC):
    """Contract for text generation (headlines + descriptions)."""

    #: Human-readable provider id, used in logs and stored on rows (model_used).
    name: str = "text"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 1.0,
    ) -> str:
        """Return generated text for the given prompt."""
        raise NotImplementedError


class ImageProvider(ABC):
    """Contract for branded image generation."""

    name: str = "image"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        reference_images: list[ReferenceImage] | None = None,
    ) -> bytes:
        """Return generated image bytes (PNG) for the prompt and references."""
        raise NotImplementedError
