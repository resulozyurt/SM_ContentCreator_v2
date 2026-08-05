"""
Image service (Phase 4) — branded image generation.

Takes a slot that already has a selected copy variant, builds a brand-aware
image prompt (headline text + colors/logo/layout), generates a near-finished
branded image via the image provider (Gemini primary, OpenAI fallback) using the
brand's reference images, uploads it to the Google Drive review folder, records
an Asset row, and advances the slot to `image_review` (human checkpoint #3).
"""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.brands.profiles import BrandProfile, load_brand
from app.db.base import AssetStatus, PipelineStatus
from app.db.models import Asset, CalendarSlot, CopyVariant
from app.providers.base import ImageProvider, ProviderError, ReferenceImage
from app.providers.factory import get_image_provider
from app.storage.base import Storage, StorageError
from app.storage.drive import DriveStorage

logger = logging.getLogger(__name__)

# Gemini can hold brand consistency across up to 14 reference images.
MAX_REFERENCE_IMAGES = 14
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


class ImageGenerationError(RuntimeError):
    """Raised when image generation or storage fails."""


def build_image_prompt(brand: BrandProfile, slot: CalendarSlot) -> str:
    """Compose the image prompt from the selected headline + brand visual rules."""
    headline = slot.selected_headline or slot.topic
    colors = brand.colors
    visual_style = brand.extra.get("visual_style", "").strip()

    return (
        f"Create a polished, near-finished social media marketing image for the "
        f"brand {brand.name}.\n"
        f"Headline text to render clearly inside the image: \"{headline}\".\n"
        f"Brand colors — accent: {colors.get('accent')}, "
        f"heading/blocks: {colors.get('heading')}, background: {colors.get('background')}. "
        f"Put accent words inside a rounded pill using the accent color.\n"
        f"Visual direction: {visual_style}\n"
        f"Match the layout, logo placement, and style of the reference images. "
        f"High resolution, clean composition, generous white space."
    )


def load_reference_images(
    brand: BrandProfile, *, limit: int = MAX_REFERENCE_IMAGES
) -> list[ReferenceImage]:
    """Load up to `limit` reference images from the brand's reference folder."""
    folder = Path(brand.reference_set_path)
    if not folder.is_dir():
        logger.warning("Reference folder missing for %s: %s", brand.key, folder)
        return []
    refs: list[ReferenceImage] = []
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() not in _IMAGE_EXTS:
            continue
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        refs.append(ReferenceImage(data=path.read_bytes(), mime_type=mime))
        if len(refs) >= limit:
            break
    return refs


def generate_image(
    session: Session,
    slot: CalendarSlot,
    *,
    provider: ImageProvider | None = None,
    storage: Storage | None = None,
) -> Asset:
    """
    Generate a branded image for the slot, upload it to the review folder, and
    record an Asset (status=review). Advances the slot to `image_review`.
    Requires the slot to have a selected copy variant. Does not commit.
    """
    if slot.status not in (PipelineStatus.copy_selected, PipelineStatus.image_review):
        raise ImageGenerationError(
            f"Slot {slot.id} is '{slot.status.value}'; expected copy_selected."
        )
    if not slot.selected_headline:
        raise ImageGenerationError(f"Slot {slot.id} has no selected headline.")

    brand = load_brand(slot.brand.value)
    provider = provider or get_image_provider(with_fallback=True)
    storage = storage or DriveStorage()

    prompt = build_image_prompt(brand, slot)
    references = load_reference_images(brand)

    try:
        image_bytes = provider.generate(prompt, reference_images=references)
    except ProviderError as exc:
        raise ImageGenerationError(f"Image provider failed: {exc}") from exc

    filename = f"{slot.brand.value}_{slot.solution.value}_slot{slot.id}.png"
    try:
        stored = storage.upload_image(filename, image_bytes, mime_type="image/png")
    except StorageError as exc:
        raise ImageGenerationError(f"Storage failed: {exc}") from exc

    selected_variant_id = _selected_variant_id(session, slot)
    asset = Asset(
        slot_id=slot.id,
        copy_variant_id=selected_variant_id,
        image_url=stored.url,
        status=AssetStatus.review,
        model_used=provider.name,
    )
    session.add(asset)

    slot.final_image_url = stored.url
    slot.status = PipelineStatus.image_review
    session.flush()
    logger.info("Stored image for slot %s at %s.", slot.id, stored.url)
    return asset


def _selected_variant_id(session: Session, slot: CalendarSlot) -> int | None:
    row = session.scalars(
        select(CopyVariant.id)
        .where(CopyVariant.slot_id == slot.id, CopyVariant.is_selected.is_(True))
        .limit(1)
    ).first()
    return row
