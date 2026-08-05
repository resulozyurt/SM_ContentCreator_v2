"""
ORM models — the pipeline data layer (single source of truth).

A `CalendarSlot` is one content item flowing through the pipeline. Its `status`
column is the state machine (see PipelineStatus). Copy variants and image assets
hang off a slot. `Trend` rows are raw legitimate trend input that seed slots.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import (
    AssetStatus,
    Base,
    Brand,
    PipelineStatus,
    Solution,
    asset_status_enum,
    brand_enum,
    pipeline_status_enum,
    solution_enum,
)


class Trend(Base):
    """Raw trend input from legitimate sources (RSS, Google Trends, news)."""

    __tablename__ = "trends"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand: Mapped[Brand] = mapped_column(brand_enum, index=True)
    solution: Mapped[Solution] = mapped_column(solution_enum)
    source: Mapped[str] = mapped_column(String(255))  # e.g. feed name / "google_trends"
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    slots: Mapped[list["CalendarSlot"]] = relationship(back_populates="trend")


class CalendarSlot(Base):
    """A single content item / pipeline row. This is the source of truth."""

    __tablename__ = "calendar_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand: Mapped[Brand] = mapped_column(brand_enum, index=True)
    solution: Mapped[Solution] = mapped_column(solution_enum)
    scheduled_date: Mapped[date] = mapped_column(Date, index=True)
    topic: Mapped[str] = mapped_column(String(512))  # theme / angle for the post
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[PipelineStatus] = mapped_column(
        pipeline_status_enum,
        default=PipelineStatus.draft,
        server_default=PipelineStatus.draft.value,
        index=True,
    )

    trend_id: Mapped[int | None] = mapped_column(
        ForeignKey("trends.id", ondelete="SET NULL"), nullable=True
    )

    # Denormalized winners for quick reads by the admin panel.
    selected_headline: Mapped[str | None] = mapped_column(String(512), nullable=True)
    selected_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    trend: Mapped["Trend | None"] = relationship(back_populates="slots")
    copy_variants: Mapped[list["CopyVariant"]] = relationship(
        back_populates="slot", cascade="all, delete-orphan"
    )
    assets: Mapped[list["Asset"]] = relationship(
        back_populates="slot", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_calendar_brand_date", "brand", "scheduled_date"),
    )


class CopyVariant(Base):
    """A generated headline + description variant for a calendar slot."""

    __tablename__ = "copy_variants"

    id: Mapped[int] = mapped_column(primary_key=True)
    slot_id: Mapped[int] = mapped_column(
        ForeignKey("calendar_slots.id", ondelete="CASCADE"), index=True
    )
    headline: Mapped[str] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)
    model_used: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    slot: Mapped["CalendarSlot"] = relationship(back_populates="copy_variants")


class Asset(Base):
    """A generated branded image for a calendar slot (stored in Google Drive)."""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    slot_id: Mapped[int] = mapped_column(
        ForeignKey("calendar_slots.id", ondelete="CASCADE"), index=True
    )
    copy_variant_id: Mapped[int | None] = mapped_column(
        ForeignKey("copy_variants.id", ondelete="SET NULL"), nullable=True
    )
    image_url: Mapped[str] = mapped_column(String(1024))  # Drive link / file id
    status: Mapped[AssetStatus] = mapped_column(
        asset_status_enum,
        default=AssetStatus.review,
        server_default=AssetStatus.review.value,
    )
    model_used: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    slot: Mapped["CalendarSlot"] = relationship(back_populates="assets")
