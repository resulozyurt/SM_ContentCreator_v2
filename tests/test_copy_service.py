"""
Tests for the copy service (Phase 3).

Runs against an in-memory SQLite DB with a fake text provider — no network, no
API keys. Verifies prompt building, robust JSON parsing, row persistence, and
the selection / status-advance logic.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base, Brand, PipelineStatus, Solution
from app.db.models import CalendarSlot
from app.providers.base import TextProvider
from app.services import copy as copy_service


class FakeTextProvider(TextProvider):
    """Returns canned JSON, wrapped in a code fence + prose, to exercise parsing."""

    name = "fake"

    def __init__(self, payload: str) -> None:
        self._payload = payload
        self.last_system: str | None = None
        self.last_prompt: str | None = None

    def generate(self, prompt, *, system=None, max_tokens=1024, temperature=1.0):
        self.last_system = system
        self.last_prompt = prompt
        return self._payload


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://")  # in-memory
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _make_slot(session: Session, brand=Brand.fieldpie, solution=Solution.merchandising):
    import datetime

    slot = CalendarSlot(
        brand=brand,
        solution=solution,
        scheduled_date=datetime.date(2026, 9, 1),
        topic="Shelf audits that actually fix the shelf",
    )
    session.add(slot)
    session.flush()
    return slot


def test_generate_and_select(session: Session):
    slot = _make_slot(session)
    payload = (
        "Here are your variants:\n```json\n"
        '[{"headline": "Photos Don\'t Fix Shelves. Actions Do.",'
        ' "description": "Turn every audit photo into a task."},'
        '{"headline": "See the Shelf. Fix the Shelf.",'
        ' "description": "Real-time gaps, real-time corrections."}]\n```'
    )
    provider = FakeTextProvider(payload)

    variants = copy_service.generate_variants(session, slot, n=2, provider=provider)

    assert len(variants) == 2
    assert all(v.id is not None for v in variants)
    assert variants[0].model_used == "fake"
    # Brand voice + English instruction flowed into the system prompt.
    assert "FieldPie" in provider.last_system
    assert "American English" in provider.last_system

    chosen = copy_service.select_variant(session, slot, variants[1].id)

    assert chosen.is_selected is True
    assert variants[0].is_selected is False
    assert slot.selected_headline == "See the Shelf. Fix the Shelf."
    assert slot.status is PipelineStatus.copy_selected


def test_evatro_uses_turkish_instruction(session: Session):
    slot = _make_slot(session, brand=Brand.evatro, solution=Solution.merchandising)
    provider = FakeTextProvider(
        '[{"headline": "Ürün Stokta, Peki Rafta mı?",'
        ' "description": "Rafı görmeden satışı kaybedersin."}]'
    )
    copy_service.generate_variants(session, slot, n=1, provider=provider)
    assert "Türkçe" in provider.last_system
    assert "Evatro" in provider.last_system


def test_bad_json_raises(session: Session):
    slot = _make_slot(session)
    provider = FakeTextProvider("sorry, no json here")
    with pytest.raises(copy_service.CopyGenerationError):
        copy_service.generate_variants(session, slot, n=3, provider=provider)


def test_select_unknown_variant_raises(session: Session):
    slot = _make_slot(session)
    provider = FakeTextProvider('[{"headline": "H", "description": "D"}]')
    copy_service.generate_variants(session, slot, n=1, provider=provider)
    with pytest.raises(copy_service.CopyGenerationError):
        copy_service.select_variant(session, slot, 9999)
