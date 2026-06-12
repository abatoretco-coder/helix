"""add contract tables

Revision ID: 20260612_01
Revises:
Create Date: 2026-06-12
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260612_01"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profiles (
            id BIGSERIAL PRIMARY KEY,
            profile_id TEXT NOT NULL UNIQUE,
            interests TEXT[],
            muted_sources TEXT[],
            languages TEXT[],
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_feedback (
            id BIGSERIAL PRIMARY KEY,
            profile_id TEXT NOT NULL,
            article_id BIGINT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
            signal TEXT NOT NULL,
            value INTEGER,
            context JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_feedback_profile_article ON user_feedback(profile_id, article_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_user_feedback_profile_article")
    op.execute("DROP TABLE IF EXISTS user_feedback")
    op.execute("DROP TABLE IF EXISTS user_profiles")
