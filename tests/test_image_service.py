"""
Tests for the image service (Phase 4).

Uses a fake image provider + fake storage + in-memory SQLite — no network, no
Google credentials. Verifies prompt building, reference loading, the Asset row,
status advance, and preconditions.
"""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.brands.profiles import load_brand
from app.db.base import AssetStatus, Base, Brand, PipelineStatus, Solution
from app.db.models import Asset, CalendarSlot, CopyVariant
from app.providers.base import ImageProvider, ReferenceImage
from app.services import image as image_service
from app.storage.base import Storage, StoredFile


class FakeImageProvider(ImageProvider):
    name = "fake_image"

    def __init__(self) -> None:
        self.last_prompt: str | None = None
        self.last_refs: list[ReferenceImage] | None = None

    def generate(self, prompt, *, reference_images=None):
        self.last_prompt = prompt
        self.last_refs = reference_images
        return b"FAKE_PNG_BYTES"


class FakeStorage(Storage):
    name = "fake_storage"

    def __init__(self) -> None:
        self.uploads: list[tuple[str, bytes]] = []

    def upload_image(self, filename, data, *, mime_type="image/png"):
        self.uploads.append((filename, data))
        return StoredFile(id="fileid123", url="https://drive.example/fileid123")


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _slot_with_selected_copy(session: Session) -> CalendarSlot:
    slot = CalendarSlot(
        brand=Brand.fieldpie,
        solution=Solution.merchandising,
        scheduled_date=datetime.date(2026, 9, 1),
        topic="Shelf audits",
        status=PipelineStatus.copy_selected,
        selected_headline="Photos Don't Fix Shelves. Actions Do.",
    )
    session.add(slot)
    session.flush()
    variant = CopyVariant(
        slot_id=slot.id, headline="H", description="D", is_selected=True
    )
    session.add(variant)
    session.flush()
    return slot


def test_generate_image_happy_path(session: Session):
    slot = _slot_with_selected_copy(session)
    provider, storage = FakeImageProvider(), FakeStorage()

    asset = image_service.generate_image(
        session, slot, provider=provider, storage=storage
    )

    assert isinstance(asset, Asset)
    assert asset.status is AssetStatus.review
    assert asset.image_url == "https://drive.example/fileid123"
    assert asset.model_used == "fake_image"
    assert slot.status is PipelineStatus.image_review
    assert slot.final_image_url == "https://drive.example/fileid123"
    # The selected headline made it into the prompt.
    assert "Photos Don't Fix Shelves" in provider.last_prompt
    assert len(storage.uploads) == 1
    assert storage.uploads[0][0] == "fieldpie_merchandising_slot1.png"


def test_requires_copy_selected(session: Session):
    slot = CalendarSlot(
        brand=Brand.evatro,
        solution=Solution.merchandising,
        scheduled_date=datetime.date(2026, 9, 1),
        topic="X",
        status=PipelineStatus.draft,
    )
    session.add(slot)
    session.flush()
    with pytest.raises(image_service.ImageGenerationError):
        image_service.generate_image(
            session, slot, provider=FakeImageProvider(), storage=FakeStorage()
        )


def test_build_prompt_uses_brand_colors():
    brand = load_brand("fieldpie")
    slot = CalendarSlot(
        brand=Brand.fieldpie,
        solution=Solution.merchandising,
        scheduled_date=datetime.date(2026, 9, 1),
        topic="t",
        selected_headline="Hook",
    )
    prompt = image_service.build_image_prompt(brand, slot)
    assert "Hook" in prompt
    assert brand.colors["accent"] in prompt
    assert "FieldPie" in prompt
