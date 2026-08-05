"""SQLAlchemy declarative base and shared enums for the pipeline schema."""

from __future__ import annotations

import enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class Brand(str, enum.Enum):
    """The two isolated brand identities."""

    fieldpie = "fieldpie"
    evatro = "evatro"


class Solution(str, enum.Enum):
    """Solution areas content is produced for."""

    merchandising = "merchandising"
    field_audit = "field_audit"
    field_sales = "field_sales"
    home_service = "home_service"
    ai = "ai"
    general = "general"


class PipelineStatus(str, enum.Enum):
    """
    State machine for a content item as it flows through the pipeline.

    draft              -> created (from a trend or manually), awaiting calendar approval
    calendar_approved  -> HUMAN CHECKPOINT #1 passed; ready for copy generation
    copy_selected      -> HUMAN CHECKPOINT #2 passed; a copy variant is chosen
    image_review       -> image generated and sitting in the Drive review folder
    approved           -> HUMAN CHECKPOINT #3 passed; ready for manual Canva + publish
    published          -> posted (recorded manually)
    rejected           -> dropped at any checkpoint
    """

    draft = "draft"
    calendar_approved = "calendar_approved"
    copy_selected = "copy_selected"
    image_review = "image_review"
    approved = "approved"
    published = "published"
    rejected = "rejected"


class AssetStatus(str, enum.Enum):
    """Status of a generated image asset."""

    review = "review"      # generated, awaiting human approval
    approved = "approved"  # selected as the final image
    rejected = "rejected"  # discarded


# Shared enum type instances. Reusing one instance per enum name means the
# Postgres CREATE TYPE happens exactly once even when the type is used across
# multiple tables (e.g. `brand` in both trends and calendar_slots).
brand_enum = SAEnum(Brand, name="brand")
solution_enum = SAEnum(Solution, name="solution")
pipeline_status_enum = SAEnum(PipelineStatus, name="pipeline_status")
asset_status_enum = SAEnum(AssetStatus, name="asset_status")
