"""initial pipeline schema

Revision ID: f821b6f74a13
Revises:
Create Date: 2026-08-05

Creates the pipeline data layer: trends, calendar_slots (source of truth with the
status state machine), copy_variants, assets. Enum types are created once,
explicitly, so shared enums (brand, solution) do not trigger a duplicate
CREATE TYPE on Postgres.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f821b6f74a13"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Enum types. create_type=False so op.create_table does NOT auto-emit CREATE TYPE;
# we create/drop them explicitly (once) below.
brand_enum = postgresql.ENUM("fieldpie", "evatro", name="brand", create_type=False)
solution_enum = postgresql.ENUM(
    "merchandising",
    "field_audit",
    "field_sales",
    "home_service",
    "ai",
    "general",
    name="solution",
    create_type=False,
)
pipeline_status_enum = postgresql.ENUM(
    "draft",
    "calendar_approved",
    "copy_selected",
    "image_review",
    "approved",
    "published",
    "rejected",
    name="pipeline_status",
    create_type=False,
)
asset_status_enum = postgresql.ENUM(
    "review", "approved", "rejected", name="asset_status", create_type=False
)

_ALL_ENUMS = (brand_enum, solution_enum, pipeline_status_enum, asset_status_enum)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in _ALL_ENUMS:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "trends",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand", brand_enum, nullable=False),
        sa.Column("solution", solution_enum, nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trends_brand"), "trends", ["brand"], unique=False)

    op.create_table(
        "calendar_slots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand", brand_enum, nullable=False),
        sa.Column("solution", solution_enum, nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("topic", sa.String(length=512), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            pipeline_status_enum,
            server_default="draft",
            nullable=False,
        ),
        sa.Column("trend_id", sa.Integer(), nullable=True),
        sa.Column("selected_headline", sa.String(length=512), nullable=True),
        sa.Column("selected_description", sa.Text(), nullable=True),
        sa.Column("final_image_url", sa.String(length=1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["trend_id"], ["trends.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_calendar_brand_date",
        "calendar_slots",
        ["brand", "scheduled_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_calendar_slots_brand"), "calendar_slots", ["brand"], unique=False
    )
    op.create_index(
        op.f("ix_calendar_slots_scheduled_date"),
        "calendar_slots",
        ["scheduled_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_calendar_slots_status"), "calendar_slots", ["status"], unique=False
    )

    op.create_table(
        "copy_variants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slot_id", sa.Integer(), nullable=False),
        sa.Column("headline", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_selected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("model_used", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["slot_id"], ["calendar_slots.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_copy_variants_slot_id"), "copy_variants", ["slot_id"], unique=False
    )

    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slot_id", sa.Integer(), nullable=False),
        sa.Column("copy_variant_id", sa.Integer(), nullable=True),
        sa.Column("image_url", sa.String(length=1024), nullable=False),
        sa.Column(
            "status", asset_status_enum, server_default="review", nullable=False
        ),
        sa.Column("model_used", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["copy_variant_id"], ["copy_variants.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["slot_id"], ["calendar_slots.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assets_slot_id"), "assets", ["slot_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index(op.f("ix_assets_slot_id"), table_name="assets")
    op.drop_table("assets")
    op.drop_index(op.f("ix_copy_variants_slot_id"), table_name="copy_variants")
    op.drop_table("copy_variants")
    op.drop_index(op.f("ix_calendar_slots_status"), table_name="calendar_slots")
    op.drop_index(op.f("ix_calendar_slots_scheduled_date"), table_name="calendar_slots")
    op.drop_index(op.f("ix_calendar_slots_brand"), table_name="calendar_slots")
    op.drop_index("ix_calendar_brand_date", table_name="calendar_slots")
    op.drop_table("calendar_slots")
    op.drop_index(op.f("ix_trends_brand"), table_name="trends")
    op.drop_table("trends")

    for enum_type in reversed(_ALL_ENUMS):
        enum_type.drop(bind, checkfirst=True)
