"""add agent tasks

Revision ID: 20260627_04
Revises: 20260627_03
Create Date: 2026-06-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260627_04"
down_revision = "20260627_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_tasks",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("agent_id", sa.Text(), nullable=False, server_default="jarvis"),
        sa.Column("task_type", sa.Text(), nullable=False, server_default="synthesis"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="queued"),
        sa.Column("priority", sa.Integer(), server_default="2"),
        sa.Column("language", sa.Text(), server_default="fr"),
        sa.Column("input_payload", postgresql.JSONB()),
        sa.Column("result_payload", postgresql.JSONB()),
        sa.Column("error_message", sa.Text()),
        sa.Column("source_article_ids", postgresql.ARRAY(sa.BigInteger()), server_default="{}"),
        sa.Column("memory_id", sa.BigInteger(), sa.ForeignKey("agent_memories.id", ondelete="SET NULL")),
        sa.Column("claimed_at", sa.DateTime()),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("failed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_agent_tasks_agent_status_priority",
        "agent_tasks",
        ["agent_id", "status", "priority"],
    )
    op.create_index(
        "ix_agent_tasks_status_created",
        "agent_tasks",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_tasks_status_created", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_agent_status_priority", table_name="agent_tasks")
    op.drop_table("agent_tasks")
