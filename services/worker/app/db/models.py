from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session_async import Base


class Source(Base):
    __tablename__ = "sources"

    id                  = Column(Integer, primary_key=True)
    name                = Column(Text, nullable=False)
    source_type         = Column(Text, nullable=False)
    url                 = Column(Text)
    query               = Column(Text)
    country             = Column(Text)
    language            = Column(Text, default="en")
    category            = Column(Text, default="general")
    priority            = Column(Integer, default=3)
    refresh_minutes     = Column(Integer, default=60)
    extraction_strategy = Column(Text, default="article")
    enabled             = Column(Boolean, default=True)
    last_checked_at     = Column(DateTime)
    last_success_at     = Column(DateTime)
    error_count         = Column(Integer, default=0)
    created_at          = Column(DateTime, server_default=func.now())
    updated_at          = Column(DateTime, server_default=func.now(), onupdate=func.now())

    raw_items = relationship("RawItem", back_populates="source", lazy="dynamic")
    articles  = relationship("Article", back_populates="source", lazy="dynamic")


class RawItem(Base):
    __tablename__ = "raw_items"

    id              = Column(BigInteger, primary_key=True)
    source_id       = Column(Integer, ForeignKey("sources.id", ondelete="SET NULL"))
    url             = Column(Text, nullable=False)
    normalized_url  = Column(Text, unique=True)
    canonical_url   = Column(Text)
    title           = Column(Text)
    snippet         = Column(Text)
    published_at    = Column(DateTime)
    discovered_at   = Column(DateTime, server_default=func.now())
    raw_payload     = Column(JSONB)
    status          = Column(Text, default="new")
    error_message   = Column(Text)
    retry_count     = Column(Integer, default=0)
    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, server_default=func.now(), onupdate=func.now())

    source  = relationship("Source", back_populates="raw_items")
    article = relationship("Article", back_populates="raw_item", uselist=False)


class Article(Base):
    __tablename__ = "articles"

    id                = Column(BigInteger, primary_key=True)
    raw_item_id       = Column(BigInteger, ForeignKey("raw_items.id", ondelete="SET NULL"))
    source_id         = Column(Integer, ForeignKey("sources.id", ondelete="SET NULL"))
    url               = Column(Text, nullable=False)
    normalized_url    = Column(Text)
    canonical_url     = Column(Text)
    title             = Column(Text)
    description       = Column(Text)
    text_content      = Column(Text)
    author            = Column(Text)
    language          = Column(Text)
    published_at      = Column(DateTime)
    discovered_at     = Column(DateTime)
    extracted_at      = Column(DateTime, server_default=func.now())
    image_url         = Column(Text)
    top_image_url     = Column(Text)
    word_count        = Column(Integer)
    content_hash      = Column(Text, unique=True)
    quality_score     = Column(Numeric(5, 2), default=0)
    extractor_used    = Column(Text)
    raw_html_path     = Column(Text)
    raw_json_path     = Column(Text)
    extraction_status = Column(Text, default="success")
    created_at        = Column(DateTime, server_default=func.now())
    updated_at        = Column(DateTime, server_default=func.now(), onupdate=func.now())

    source   = relationship("Source", back_populates="articles")
    raw_item = relationship("RawItem", back_populates="article")
    ai       = relationship("ArticleAI", back_populates="article", uselist=False, cascade="all, delete-orphan")
    clusters = relationship("ArticleCluster", back_populates="article", cascade="all, delete-orphan")


class ArticleAI(Base):
    __tablename__ = "article_ai"

    article_id               = Column(BigInteger, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True)
    summary_short            = Column(Text)
    summary_long             = Column(Text)
    category                 = Column(Text)
    topics                   = Column(ARRAY(Text))
    entities                 = Column(JSONB)
    sentiment                = Column(Text)
    importance_score         = Column(Numeric(4, 3))
    novelty_score            = Column(Numeric(4, 3))
    personal_relevance_score = Column(Numeric(4, 3))
    quality_score            = Column(Numeric(4, 3))
    freshness_score          = Column(Numeric(4, 3))
    source_score             = Column(Numeric(4, 3))
    final_score              = Column(Numeric(4, 3))
    embedding                = Column(Vector(768))
    model_name               = Column(Text)
    processed_at             = Column(DateTime, server_default=func.now())

    article = relationship("Article", back_populates="ai")


class Cluster(Base):
    __tablename__ = "clusters"

    id               = Column(BigInteger, primary_key=True)
    main_title       = Column(Text)
    main_summary     = Column(Text)
    topic            = Column(Text)
    language         = Column(Text)
    first_seen_at    = Column(DateTime, server_default=func.now())
    last_seen_at     = Column(DateTime, server_default=func.now())
    article_count    = Column(Integer, default=0)
    importance_score = Column(Numeric(4, 3))
    created_at       = Column(DateTime, server_default=func.now())
    updated_at       = Column(DateTime, server_default=func.now(), onupdate=func.now())

    articles = relationship("ArticleCluster", back_populates="cluster", cascade="all, delete-orphan")


class ArticleCluster(Base):
    __tablename__ = "article_clusters"

    article_id       = Column(BigInteger, ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True)
    cluster_id       = Column(BigInteger, ForeignKey("clusters.id", ondelete="CASCADE"), primary_key=True)
    similarity_score = Column(Numeric(4, 3))
    created_at       = Column(DateTime, server_default=func.now())

    article = relationship("Article", back_populates="clusters")
    cluster = relationship("Cluster", back_populates="articles")


class Briefing(Base):
    __tablename__ = "briefings"

    id           = Column(BigInteger, primary_key=True)
    period       = Column(Text, nullable=False)
    period_date  = Column(DateTime, nullable=False)
    category     = Column(Text, default="all")
    content      = Column(Text)
    article_ids  = Column(ARRAY(BigInteger))
    cluster_ids  = Column(ARRAY(BigInteger))
    generated_at = Column(DateTime, server_default=func.now())


class ProcessingLog(Base):
    __tablename__ = "processing_logs"

    id          = Column(BigInteger, primary_key=True)
    item_type   = Column(Text, nullable=False)
    item_id     = Column(BigInteger)
    step        = Column(Text, nullable=False)
    status      = Column(Text, nullable=False)
    message     = Column(Text)
    payload     = Column(JSONB)
    duration_ms = Column(Integer)
    created_at  = Column(DateTime, server_default=func.now())


class ArticleUserState(Base):
    __tablename__ = "article_user_state"

    id = Column(BigInteger, primary_key=True)
    profile_id = Column(Text, nullable=False, default="default")
    article_id = Column(BigInteger, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    is_read = Column(Boolean, default=False)
    is_saved = Column(Boolean, default=False)
    is_hidden = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class WatchlistEntity(Base):
    __tablename__ = "watchlist_entities"

    id = Column(BigInteger, primary_key=True)
    name = Column(Text, nullable=False)
    entity_type = Column(Text, default="company")
    priority = Column(Integer, default=2)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class EntityMention(Base):
    __tablename__ = "entity_mentions"

    id = Column(BigInteger, primary_key=True)
    article_id = Column(BigInteger, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    watchlist_entity_id = Column(BigInteger, ForeignKey("watchlist_entities.id", ondelete="CASCADE"), nullable=False)
    mention_count = Column(Integer, default=1)
    matched_context = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class ResearchProject(Base):
    __tablename__ = "research_projects"

    id = Column(BigInteger, primary_key=True)
    slug = Column(Text, nullable=False, unique=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    keywords = Column(ARRAY(Text), default=[])
    priority = Column(Integer, default=2)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ProjectArticle(Base):
    __tablename__ = "project_articles"

    id = Column(BigInteger, primary_key=True)
    project_id = Column(BigInteger, ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False)
    article_id = Column(BigInteger, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    matched_keywords = Column(ARRAY(Text), default=[])
    created_at = Column(DateTime, server_default=func.now())


class NotificationChannel(Base):
    __tablename__ = "notification_channels"

    id = Column(BigInteger, primary_key=True)
    name = Column(Text, nullable=False)
    channel_type = Column(Text, nullable=False)
    target_url = Column(Text)
    auth_token = Column(Text)
    channel_config = Column("config", JSONB)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(BigInteger, primary_key=True)
    name = Column(Text, nullable=False)
    event_type = Column(Text, nullable=False)
    rule_config = Column("config", JSONB)
    channel_id = Column(BigInteger, ForeignKey("notification_channels.id", ondelete="SET NULL"))
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ExportJob(Base):
    __tablename__ = "export_jobs"

    id = Column(BigInteger, primary_key=True)
    export_type = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="queued")
    output_path = Column(Text)
    details = Column(JSONB)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class RetentionJob(Base):
    __tablename__ = "retention_jobs"

    id = Column(BigInteger, primary_key=True)
    job_type = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="queued")
    cutoff_days = Column(Integer)
    deleted_count = Column(Integer, default=0)
    details = Column(JSONB)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


Index("ix_article_user_state_profile_article", ArticleUserState.profile_id, ArticleUserState.article_id, unique=True)
Index("ix_watchlist_entities_name", WatchlistEntity.name)
Index("ix_entity_mentions_article", EntityMention.article_id)
Index("ix_research_projects_slug", ResearchProject.slug, unique=True)
Index("ix_project_articles_project_article", ProjectArticle.project_id, ProjectArticle.article_id, unique=True)
Index("ix_alert_rules_event_type", AlertRule.event_type)
