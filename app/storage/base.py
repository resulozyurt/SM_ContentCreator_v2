"""
Storage interface.

Generated images go to a storage backend behind this interface. Today the
backend is Google Drive; putting it behind one contract means swapping to
another store later (e.g. Cloudflare R2) is a single implementation file.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class StorageError(RuntimeError):
    """Raised when a storage operation fails."""


@dataclass
class StoredFile:
    """A file that has been persisted to storage."""

    id: str
    url: str


class Storage(ABC):
    """Contract for storing generated image bytes."""

    name: str = "storage"

    @abstractmethod
    def upload_image(
        self, filename: str, data: bytes, *, mime_type: str = "image/png"
    ) -> StoredFile:
        """Persist image bytes and return a reference (id + viewable URL)."""
        raise NotImplementedError
