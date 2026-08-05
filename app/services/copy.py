"""
Copy service (Phase 3) — headline + description generation.

Takes a CalendarSlot, loads its brand profile (voice + language), builds a
brand-aware prompt with solution context, asks the text provider for N
scroll-stopping variants, and persists them as CopyVariant rows.

Human checkpoint #2 happens after this: a person reviews the variants and calls
select_variant(), which advances the slot to `copy_selected`.

Language is brand-driven: FieldPie -> American English, Evatro -> Turkish. The
instruction comes from the brand profile, so identities never cross.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.brands.profiles import BrandProfile, load_brand
from app.db.base import PipelineStatus
from app.db.models import CalendarSlot, CopyVariant
from app.providers.base import ProviderError, TextProvider
from app.providers.factory import get_text_provider

logger = logging.getLogger(__name__)

# Short context per solution area, injected into the prompt so the model knows
# what the post is about. FieldPie serves all six; Evatro a subset.
SOLUTION_CONTEXT: dict[str, str] = {
    "merchandising": (
        "Retail merchandising execution — making sure products are on the shelf, "
        "priced right, and displayed to plan; closing the gap between planogram "
        "and reality in stores."
    ),
    "field_audit": (
        "Field audits and store checks — structured data collection in the field, "
        "photo evidence, and turning findings into corrective actions."
    ),
    "field_sales": (
        "Field sales enablement — reps in the field taking orders, tracking visits, "
        "and hitting targets with the right data at the right moment."
    ),
    "home_service": (
        "Home service operations — scheduling, dispatching and tracking technicians "
        "who do work at customer locations."
    ),
    "ai": (
        "AI for field operations — using automation and image recognition to turn "
        "field photos and data into instant, actionable insight."
    ),
    "general": "General brand awareness and thought leadership for field operations.",
}


class CopyGenerationError(RuntimeError):
    """Raised when variant generation or parsing fails."""


def build_copy_prompt(brand: BrandProfile, slot: CalendarSlot, n: int) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for generating `n` copy variants."""
    solution_key = slot.solution.value
    solution_ctx = SOLUTION_CONTEXT.get(solution_key, solution_key)

    language_line = (
        "Write everything in natural, native American English."
        if brand.language.startswith("en")
        else "Her şeyi doğal, yerel Türkçe yaz (çeviri gibi durmasın)."
    )

    system = (
        f"{brand.voice_prompt.strip()}\n\n"
        f"{language_line}\n"
        f"You are writing social media copy for the brand {brand.name}."
    )

    user = (
        f"Solution area: {solution_key} — {solution_ctx}\n"
        f"Post topic / angle: {slot.topic}\n"
        + (f"Extra notes: {slot.notes}\n" if slot.notes else "")
        + f"\nProduce {n} distinct, scroll-stopping variants. Each has:\n"
        "- \"headline\": a short, punchy hook (max ~10 words)\n"
        "- \"description\": 1-3 sentence post caption that expands the hook\n\n"
        "Return ONLY a JSON array, no prose, no code fences. Example:\n"
        '[{"headline": "...", "description": "..."}]'
    )
    return system, user


def _parse_variants(text: str) -> list[dict[str, str]]:
    """Parse the model output into a list of {headline, description} dicts."""
    cleaned = text.strip()
    # Strip markdown code fences if the model wrapped the JSON.
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1]
        if cleaned.lstrip().lower().startswith("json"):
            cleaned = cleaned.lstrip()[4:]
    cleaned = cleaned.strip()
    # If there is surrounding prose, grab the outermost JSON array.
    if not cleaned.startswith("["):
        start, end = cleaned.find("["), cleaned.rfind("]")
        if start == -1 or end == -1:
            raise CopyGenerationError(f"No JSON array found in output: {text[:120]!r}")
        cleaned = cleaned[start : end + 1]

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise CopyGenerationError(f"Invalid JSON from model: {exc}") from exc

    variants: list[dict[str, str]] = []
    for item in data:
        headline = (item.get("headline") or "").strip()
        description = (item.get("description") or "").strip()
        if headline and description:
            variants.append({"headline": headline, "description": description})
    if not variants:
        raise CopyGenerationError("Model returned no usable variants.")
    return variants


def generate_variants(
    session: Session,
    slot: CalendarSlot,
    *,
    n: int = 5,
    provider: TextProvider | None = None,
) -> list[CopyVariant]:
    """Generate and persist `n` copy variants for the slot. Does not commit."""
    brand = load_brand(slot.brand.value)
    provider = provider or get_text_provider()
    system, user = build_copy_prompt(brand, slot, n)

    try:
        raw = provider.generate(user, system=system, max_tokens=1500, temperature=1.0)
    except ProviderError as exc:
        raise CopyGenerationError(f"Text provider failed: {exc}") from exc

    parsed = _parse_variants(raw)
    variants = [
        CopyVariant(
            slot_id=slot.id,
            headline=item["headline"],
            description=item["description"],
            model_used=provider.name,
        )
        for item in parsed
    ]
    session.add_all(variants)
    session.flush()
    logger.info(
        "Generated %d copy variants for slot %s (%s/%s).",
        len(variants),
        slot.id,
        slot.brand.value,
        slot.solution.value,
    )
    return variants


def select_variant(
    session: Session, slot: CalendarSlot, variant_id: int
) -> CopyVariant:
    """
    Human checkpoint #2: mark one variant as selected, deselect the rest,
    denormalize the winner onto the slot, and advance status to copy_selected.
    Does not commit.
    """
    variants = session.scalars(
        select(CopyVariant).where(CopyVariant.slot_id == slot.id)
    ).all()
    chosen: CopyVariant | None = None
    for variant in variants:
        is_chosen = variant.id == variant_id
        variant.is_selected = is_chosen
        if is_chosen:
            chosen = variant

    if chosen is None:
        raise CopyGenerationError(
            f"Variant {variant_id} does not belong to slot {slot.id}."
        )

    slot.selected_headline = chosen.headline
    slot.selected_description = chosen.description
    slot.status = PipelineStatus.copy_selected
    session.flush()
    logger.info("Selected variant %s for slot %s.", variant_id, slot.id)
    return chosen
