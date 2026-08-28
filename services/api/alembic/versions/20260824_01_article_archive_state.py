"""add reversible archive state to articles

Revision ID: 20260824_01
Revises: 20260816_01
Create Date: 2026-08-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260824_01"
down_revision = "20260816_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("archived_at", sa.DateTime(), nullable=True))
    op.create_index("ix_articles_archived_at", "articles", ["archived_at"])


def downgrade() -> None:
    op.drop_index("ix_articles_archived_at", table_name="articles")
    op.drop_column("articles", "archived_at")
