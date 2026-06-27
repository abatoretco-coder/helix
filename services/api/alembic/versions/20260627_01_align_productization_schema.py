"""align productization schema defaults and indexes

Revision ID: 20260627_01
Revises: 20260613_01
Create Date: 2026-06-27
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260627_01"
down_revision: Union[str, None] = "20260613_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE user_profiles ALTER COLUMN interests SET DEFAULT '{}'")
    op.execute("ALTER TABLE user_profiles ALTER COLUMN muted_sources SET DEFAULT '{}'")
    op.execute("ALTER TABLE user_profiles ALTER COLUMN languages SET DEFAULT '{}'")
    op.execute("ALTER TABLE user_feedback ALTER COLUMN value SET DEFAULT 0")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_entity_mentions_watchlist_entity "
        "ON entity_mentions(watchlist_entity_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_entity_mentions_article_watchlist_entity "
        "ON entity_mentions(article_id, watchlist_entity_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_entity_mentions_article_watchlist_entity")
    op.execute("DROP INDEX IF EXISTS ix_entity_mentions_watchlist_entity")
    op.execute("ALTER TABLE user_feedback ALTER COLUMN value DROP DEFAULT")
    op.execute("ALTER TABLE user_profiles ALTER COLUMN languages DROP DEFAULT")
    op.execute("ALTER TABLE user_profiles ALTER COLUMN muted_sources DROP DEFAULT")
    op.execute("ALTER TABLE user_profiles ALTER COLUMN interests DROP DEFAULT")
