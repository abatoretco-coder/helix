"""add auditable explicit OpenAI usage events

Revision ID: 20260816_01
Revises: 20260627_04
Create Date: 2026-08-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260816_01"
down_revision = "20260627_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "openai_usage_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime()),
    )
    op.create_index("ix_openai_usage_events_endpoint_created", "openai_usage_events", ["endpoint", "created_at"])
    op.create_index("ix_openai_usage_events_created", "openai_usage_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_openai_usage_events_created", table_name="openai_usage_events")
    op.drop_index("ix_openai_usage_events_endpoint_created", table_name="openai_usage_events")
    op.drop_table("openai_usage_events")
