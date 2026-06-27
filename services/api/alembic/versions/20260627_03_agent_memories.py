"""add agent memories

Revision ID: 20260627_03
Revises: 20260627_02
Create Date: 2026-06-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260627_03"
down_revision = "20260627_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_memories",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("agent_id", sa.Text(), nullable=False, server_default="jarvis"),
        sa.Column("memory_type", sa.Text(), nullable=False, server_default="summary"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), server_default="fr"),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), server_default="{}"),
        sa.Column("source_article_ids", postgresql.ARRAY(sa.BigInteger()), server_default="{}"),
        sa.Column("source_urls", postgresql.ARRAY(sa.Text()), server_default="{}"),
        sa.Column("confidence", sa.Numeric(4, 3)),
        sa.Column("metadata", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_agent_memories_agent_created",
        "agent_memories",
        ["agent_id", "created_at"],
    )
    op.create_index(
        "ix_agent_memories_type_created",
        "agent_memories",
        ["memory_type", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_memories_type_created", table_name="agent_memories")
    op.drop_index("ix_agent_memories_agent_created", table_name="agent_memories")
    op.drop_table("agent_memories")
