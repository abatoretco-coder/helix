"""productization phase tables

Revision ID: 20260613_01
Revises: 20260612_01
Create Date: 2026-06-13
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260613_01"
down_revision: Union[str, None] = "20260612_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS article_user_state (
            id BIGSERIAL PRIMARY KEY,
            profile_id TEXT NOT NULL DEFAULT 'default',
            article_id BIGINT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
            is_read BOOLEAN NOT NULL DEFAULT FALSE,
            is_saved BOOLEAN NOT NULL DEFAULT FALSE,
            is_hidden BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_article_user_state_profile_article ON article_user_state(profile_id, article_id)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS watchlist_entities (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            entity_type TEXT DEFAULT 'company',
            priority INTEGER DEFAULT 2,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_watchlist_entities_name ON watchlist_entities(name)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS entity_mentions (
            id BIGSERIAL PRIMARY KEY,
            article_id BIGINT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
            watchlist_entity_id BIGINT NOT NULL REFERENCES watchlist_entities(id) ON DELETE CASCADE,
            mention_count INTEGER DEFAULT 1,
            matched_context TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_entity_mentions_article ON entity_mentions(article_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS research_projects (
            id BIGSERIAL PRIMARY KEY,
            slug TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description TEXT,
            keywords TEXT[] DEFAULT '{}',
            priority INTEGER DEFAULT 2,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_research_projects_slug ON research_projects(slug)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS project_articles (
            id BIGSERIAL PRIMARY KEY,
            project_id BIGINT NOT NULL REFERENCES research_projects(id) ON DELETE CASCADE,
            article_id BIGINT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
            matched_keywords TEXT[] DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_project_articles_project_article ON project_articles(project_id, article_id)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_channels (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            channel_type TEXT NOT NULL,
            target_url TEXT,
            auth_token TEXT,
            config JSONB,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS alert_rules (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            config JSONB,
            channel_id BIGINT REFERENCES notification_channels(id) ON DELETE SET NULL,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_alert_rules_event_type ON alert_rules(event_type)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS export_jobs (
            id BIGSERIAL PRIMARY KEY,
            export_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            output_path TEXT,
            details JSONB,
            started_at TIMESTAMP,
            finished_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS retention_jobs (
            id BIGSERIAL PRIMARY KEY,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            cutoff_days INTEGER,
            deleted_count INTEGER DEFAULT 0,
            details JSONB,
            started_at TIMESTAMP,
            finished_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS retention_jobs")
    op.execute("DROP TABLE IF EXISTS export_jobs")
    op.execute("DROP INDEX IF EXISTS ix_alert_rules_event_type")
    op.execute("DROP TABLE IF EXISTS alert_rules")
    op.execute("DROP TABLE IF EXISTS notification_channels")
    op.execute("DROP INDEX IF EXISTS ix_project_articles_project_article")
    op.execute("DROP TABLE IF EXISTS project_articles")
    op.execute("DROP INDEX IF EXISTS ix_research_projects_slug")
    op.execute("DROP TABLE IF EXISTS research_projects")
    op.execute("DROP INDEX IF EXISTS ix_entity_mentions_article")
    op.execute("DROP TABLE IF EXISTS entity_mentions")
    op.execute("DROP INDEX IF EXISTS ix_watchlist_entities_name")
    op.execute("DROP TABLE IF EXISTS watchlist_entities")
    op.execute("DROP INDEX IF EXISTS ix_article_user_state_profile_article")
    op.execute("DROP TABLE IF EXISTS article_user_state")
