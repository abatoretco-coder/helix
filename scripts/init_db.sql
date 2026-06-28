-- ─────────────────────────────────────────────────────────────────────────────
-- Helix — PostgreSQL schema
-- Run automatically by Docker on first startup via init_db.sql
-- ─────────────────────────────────────────────────────────────────────────────

-- Extension vectorielle
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ── Sources ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sources (
    id               SERIAL PRIMARY KEY,
    name             TEXT NOT NULL,
    source_type      TEXT NOT NULL,       -- rss, atom, google_news_rss, reddit, hackernews, github_trending, youtube_channel, sitemap, html_page
    url              TEXT,
    query            TEXT,               -- for google_news_rss, github search, etc.
    country          TEXT,
    language         TEXT DEFAULT 'en',
    category         TEXT DEFAULT 'general',
    priority         INTEGER DEFAULT 3,  -- 1=highest (15min) .. 4=lowest (weekly)
    refresh_minutes  INTEGER DEFAULT 60,
    extraction_strategy TEXT DEFAULT 'article',
    enabled          BOOLEAN DEFAULT TRUE,
    last_checked_at  TIMESTAMP,
    last_success_at  TIMESTAMP,
    error_count      INTEGER DEFAULT 0,
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sources_enabled   ON sources(enabled);
CREATE INDEX IF NOT EXISTS idx_sources_priority  ON sources(priority);
CREATE INDEX IF NOT EXISTS idx_sources_type      ON sources(source_type);

-- ── Raw items (URLs discovered, not yet fully extracted) ──────────────────────

CREATE TABLE IF NOT EXISTS raw_items (
    id               BIGSERIAL PRIMARY KEY,
    source_id        INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    url              TEXT NOT NULL,
    normalized_url   TEXT,
    canonical_url    TEXT,
    title            TEXT,
    snippet          TEXT,
    published_at     TIMESTAMP,
    discovered_at    TIMESTAMP DEFAULT NOW(),
    raw_payload      JSONB,
    status           TEXT DEFAULT 'new',    -- new, queued_for_extraction, extracted, failed, duplicate, ignored, queued_for_ai, ai_processed, clustered
    error_message    TEXT,
    retry_count      INTEGER DEFAULT 0,
    next_retry_at    TIMESTAMP,
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW(),
    UNIQUE(normalized_url)
);

CREATE INDEX IF NOT EXISTS idx_raw_items_status        ON raw_items(status);
CREATE INDEX IF NOT EXISTS idx_raw_items_published_at  ON raw_items(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_raw_items_source_id     ON raw_items(source_id);
CREATE INDEX IF NOT EXISTS idx_raw_items_next_retry_at ON raw_items(next_retry_at);

-- ── Articles (full extracted content) ────────────────────────────────────────

CREATE TABLE IF NOT EXISTS articles (
    id                  BIGSERIAL PRIMARY KEY,
    raw_item_id         BIGINT REFERENCES raw_items(id) ON DELETE SET NULL,
    source_id           INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    url                 TEXT NOT NULL,
    normalized_url      TEXT,
    canonical_url       TEXT,
    title               TEXT,
    description         TEXT,
    text_content        TEXT,
    author              TEXT,
    language            TEXT,
    published_at        TIMESTAMP,
    discovered_at       TIMESTAMP,
    extracted_at        TIMESTAMP DEFAULT NOW(),
    image_url           TEXT,
    top_image_url       TEXT,
    word_count          INTEGER,
    content_hash        TEXT,
    quality_score       NUMERIC(5,2) DEFAULT 0,
    extractor_used      TEXT,
    raw_html_path       TEXT,
    raw_json_path       TEXT,
    extraction_status   TEXT DEFAULT 'success',
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW(),
    UNIQUE(content_hash)
);

CREATE INDEX IF NOT EXISTS idx_articles_published_at  ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_language      ON articles(language);
CREATE INDEX IF NOT EXISTS idx_articles_source_id     ON articles(source_id);
CREATE INDEX IF NOT EXISTS idx_articles_quality_score ON articles(quality_score DESC);
CREATE INDEX IF NOT EXISTS idx_articles_content_hash  ON articles(content_hash);

-- Full-text search (Postgres native, complementary to Meilisearch)
CREATE INDEX IF NOT EXISTS idx_articles_title_trgm ON articles USING GIN(title gin_trgm_ops);

-- ── AI enrichment ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS article_ai (
    article_id              BIGINT PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
    summary_short           TEXT,
    summary_long            TEXT,
    category                TEXT,
    topics                  TEXT[],
    entities                JSONB,              -- {people, companies, countries, cities, products, technologies}
    sentiment               TEXT,               -- positive, negative, neutral
    importance_score        NUMERIC(4,3),       -- 0.000 – 1.000
    novelty_score           NUMERIC(4,3),
    personal_relevance_score NUMERIC(4,3),
    quality_score           NUMERIC(4,3),
    freshness_score         NUMERIC(4,3),
    source_score            NUMERIC(4,3),
    final_score             NUMERIC(4,3),
    embedding               VECTOR(768),        -- nomic-embed-text / bge-m3
    model_name              TEXT,
    processed_at            TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_article_ai_final_score ON article_ai(final_score DESC);
CREATE INDEX IF NOT EXISTS idx_article_ai_category    ON article_ai(category);

-- IVFFlat index for fast cosine similarity search
CREATE INDEX IF NOT EXISTS idx_article_ai_embedding
    ON article_ai USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ── Clusters (same event from multiple sources) ───────────────────────────────

CREATE TABLE IF NOT EXISTS clusters (
    id               BIGSERIAL PRIMARY KEY,
    main_title       TEXT,
    main_summary     TEXT,
    topic            TEXT,
    language         TEXT,
    first_seen_at    TIMESTAMP DEFAULT NOW(),
    last_seen_at     TIMESTAMP DEFAULT NOW(),
    article_count    INTEGER DEFAULT 0,
    importance_score NUMERIC(4,3),
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clusters_last_seen_at ON clusters(last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_clusters_topic        ON clusters(topic);

CREATE TABLE IF NOT EXISTS article_clusters (
    article_id       BIGINT REFERENCES articles(id) ON DELETE CASCADE,
    cluster_id       BIGINT REFERENCES clusters(id) ON DELETE CASCADE,
    similarity_score NUMERIC(4,3),
    created_at       TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY(article_id, cluster_id)
);

-- ── Briefings ─────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS briefings (
    id               BIGSERIAL PRIMARY KEY,
    period           TEXT NOT NULL,     -- daily, weekly, monthly
    period_date      DATE NOT NULL,
    category         TEXT DEFAULT 'all',
    content          TEXT,
    article_ids      BIGINT[],
    cluster_ids      BIGINT[],
    generated_at     TIMESTAMP DEFAULT NOW(),
    UNIQUE(period, period_date, category)
);

CREATE INDEX IF NOT EXISTS idx_briefings_period_date ON briefings(period_date DESC);

-- Agent memories / syntheses -------------------------------------------------

CREATE TABLE IF NOT EXISTS agent_memories (
    id                 BIGSERIAL PRIMARY KEY,
    agent_id           TEXT NOT NULL DEFAULT 'jarvis',
    memory_type        TEXT NOT NULL DEFAULT 'summary',
    title              TEXT NOT NULL,
    content            TEXT NOT NULL,
    language           TEXT DEFAULT 'fr',
    tags               TEXT[] DEFAULT '{}',
    source_article_ids BIGINT[] DEFAULT '{}',
    source_urls        TEXT[] DEFAULT '{}',
    confidence         NUMERIC(4,3),
    "metadata"         JSONB,
    created_at         TIMESTAMP DEFAULT NOW(),
    updated_at         TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_agent_memories_agent_created ON agent_memories(agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_agent_memories_type_created ON agent_memories(memory_type, created_at DESC);

CREATE TABLE IF NOT EXISTS agent_tasks (
    id                 BIGSERIAL PRIMARY KEY,
    agent_id           TEXT NOT NULL DEFAULT 'jarvis',
    task_type          TEXT NOT NULL DEFAULT 'synthesis',
    title              TEXT NOT NULL,
    instructions       TEXT NOT NULL,
    status             TEXT NOT NULL DEFAULT 'queued',
    priority           INTEGER DEFAULT 2,
    language           TEXT DEFAULT 'fr',
    input_payload      JSONB,
    result_payload     JSONB,
    error_message      TEXT,
    source_article_ids BIGINT[] DEFAULT '{}',
    memory_id          BIGINT REFERENCES agent_memories(id) ON DELETE SET NULL,
    claimed_at         TIMESTAMP,
    completed_at       TIMESTAMP,
    failed_at          TIMESTAMP,
    created_at         TIMESTAMP DEFAULT NOW(),
    updated_at         TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_agent_tasks_agent_status_priority ON agent_tasks(agent_id, status, priority);
CREATE INDEX IF NOT EXISTS ix_agent_tasks_status_created ON agent_tasks(status, created_at DESC);

-- ── Processing logs ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS processing_logs (
    id               BIGSERIAL PRIMARY KEY,
    item_type        TEXT NOT NULL,     -- raw_item, article
    item_id          BIGINT,
    step             TEXT NOT NULL,     -- collect, extract, ai, cluster, search_index
    status           TEXT NOT NULL,     -- success, error, skip, duplicate
    message          TEXT,
    payload          JSONB,
    duration_ms      INTEGER,
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_processing_logs_item    ON processing_logs(item_type, item_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_step    ON processing_logs(step);
CREATE INDEX IF NOT EXISTS idx_processing_logs_status  ON processing_logs(status);
CREATE INDEX IF NOT EXISTS idx_processing_logs_created ON processing_logs(created_at DESC);

-- ── User profiles and feedback ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_profiles (
    id               BIGSERIAL PRIMARY KEY,
    profile_id       TEXT NOT NULL UNIQUE,
    interests        TEXT[] DEFAULT '{}',
    muted_sources    TEXT[] DEFAULT '{}',
    languages        TEXT[] DEFAULT '{}',
    "metadata"       JSONB,
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_feedback (
    id               BIGSERIAL PRIMARY KEY,
    profile_id       TEXT NOT NULL,
    article_id       BIGINT REFERENCES articles(id) ON DELETE CASCADE,
    signal           TEXT NOT NULL,
    value            INTEGER DEFAULT 0,
    context          JSONB,
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_user_feedback_profile_article ON user_feedback(profile_id, article_id);

-- ── User article state ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS article_user_state (
    id               BIGSERIAL PRIMARY KEY,
    profile_id       TEXT NOT NULL DEFAULT 'default',
    article_id       BIGINT REFERENCES articles(id) ON DELETE CASCADE,
    is_read          BOOLEAN DEFAULT FALSE,
    is_saved         BOOLEAN DEFAULT FALSE,
    is_hidden        BOOLEAN DEFAULT FALSE,
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_article_user_state_profile_article
    ON article_user_state(profile_id, article_id);

-- ── Watchlist ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS watchlist_entities (
    id               BIGSERIAL PRIMARY KEY,
    name             TEXT NOT NULL,
    entity_type      TEXT DEFAULT 'company',
    priority         INTEGER DEFAULT 2,
    enabled          BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_watchlist_entities_name ON watchlist_entities(name);

CREATE TABLE IF NOT EXISTS entity_mentions (
    id                  BIGSERIAL PRIMARY KEY,
    article_id          BIGINT REFERENCES articles(id) ON DELETE CASCADE,
    watchlist_entity_id BIGINT REFERENCES watchlist_entities(id) ON DELETE CASCADE,
    mention_count       INTEGER DEFAULT 1,
    matched_context     TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_entity_mentions_article ON entity_mentions(article_id);
CREATE INDEX IF NOT EXISTS ix_entity_mentions_watchlist_entity ON entity_mentions(watchlist_entity_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_entity_mentions_article_watchlist_entity
    ON entity_mentions(article_id, watchlist_entity_id);

-- ── Research projects ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS research_projects (
    id               BIGSERIAL PRIMARY KEY,
    slug             TEXT NOT NULL UNIQUE,
    name             TEXT NOT NULL,
    description      TEXT,
    keywords         TEXT[] DEFAULT '{}',
    priority         INTEGER DEFAULT 2,
    enabled          BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project_articles (
    id               BIGSERIAL PRIMARY KEY,
    project_id       BIGINT REFERENCES research_projects(id) ON DELETE CASCADE,
    article_id       BIGINT REFERENCES articles(id) ON DELETE CASCADE,
    matched_keywords TEXT[] DEFAULT '{}',
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_project_articles_project_article
    ON project_articles(project_id, article_id);

-- ── Alerts and notifications ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS notification_channels (
    id               BIGSERIAL PRIMARY KEY,
    name             TEXT NOT NULL,
    channel_type     TEXT NOT NULL,
    target_url       TEXT,
    auth_token       TEXT,
    config           JSONB,
    enabled          BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_rules (
    id               BIGSERIAL PRIMARY KEY,
    name             TEXT NOT NULL,
    event_type       TEXT NOT NULL,
    config           JSONB,
    channel_id       BIGINT REFERENCES notification_channels(id) ON DELETE SET NULL,
    enabled          BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_alert_rules_event_type ON alert_rules(event_type);

-- ── Export and retention jobs ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS export_jobs (
    id               BIGSERIAL PRIMARY KEY,
    export_type      TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'queued',
    output_path      TEXT,
    details          JSONB,
    started_at       TIMESTAMP,
    finished_at      TIMESTAMP,
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS retention_jobs (
    id               BIGSERIAL PRIMARY KEY,
    job_type         TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'queued',
    cutoff_days      INTEGER,
    deleted_count    INTEGER DEFAULT 0,
    details          JSONB,
    started_at       TIMESTAMP,
    finished_at      TIMESTAMP,
    created_at       TIMESTAMP DEFAULT NOW()
);

-- ── Trigger: auto-update updated_at ───────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE tbl TEXT;
BEGIN
    FOREACH tbl IN ARRAY ARRAY[
        'sources',
        'raw_items',
        'articles',
        'clusters',
        'user_profiles',
        'article_user_state',
        'watchlist_entities',
        'research_projects',
        'notification_channels',
        'alert_rules'
    ] LOOP
        EXECUTE format(
            'CREATE OR REPLACE TRIGGER trg_%s_updated_at
             BEFORE UPDATE ON %s
             FOR EACH ROW EXECUTE FUNCTION update_updated_at()',
            tbl, tbl
        );
    END LOOP;
END;
$$;
