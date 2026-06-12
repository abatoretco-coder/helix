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

from app.db.session import Base


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


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id            = Column(BigInteger, primary_key=True)
    profile_id    = Column(Text, nullable=False, unique=True)
    interests     = Column(ARRAY(Text), default=[])
    muted_sources = Column(ARRAY(Text), default=[])
    languages     = Column(ARRAY(Text), default=[])
    metadata      = Column(JSONB)
    created_at    = Column(DateTime, server_default=func.now())
    updated_at    = Column(DateTime, server_default=func.now(), onupdate=func.now())


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id         = Column(BigInteger, primary_key=True)
    profile_id = Column(Text, nullable=False)
    article_id = Column(BigInteger, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    signal     = Column(Text, nullable=False)  # useful | not_useful | saved
    value      = Column(Integer, default=0)
    context    = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())


Index("ix_user_feedback_profile_article", UserFeedback.profile_id, UserFeedback.article_id)
