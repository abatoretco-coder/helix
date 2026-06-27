"""add raw item retry backoff timestamp

Revision ID: 20260627_02
Revises: 20260627_01
Create Date: 2026-06-27
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260627_02"
down_revision: Union[str, None] = "20260627_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE raw_items ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP")
    op.execute("CREATE INDEX IF NOT EXISTS idx_raw_items_next_retry_at ON raw_items(next_retry_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_raw_items_next_retry_at")
    op.execute("ALTER TABLE raw_items DROP COLUMN IF EXISTS next_retry_at")
