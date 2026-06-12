# Helix Roadmap

## v0.1 — MVP Stabilization

Goal: make the local NAS pipeline reliable end-to-end.

### Features
- Stable Docker Compose stack
- RSS + Google News RSS collection
- Full-text extraction with fallback chain
- PostgreSQL + pgvector storage
- MinIO raw storage
- Meilisearch indexing
- Ollama summarization and embeddings
- Cluster generation
- Daily briefing generation
- Basic FastAPI endpoints
- Basic dashboard

### Tech tasks
- Add scheduler worker
- Improve smoke tests
- Improve Docker dependencies
- Improve briefing date fallback
- Add MVP closure checklist
- Add backup/restore verification

## v0.2 — Source Expansion

Goal: increase coverage and source diversity.

### Features
- Massive RSS import from OPML and awesome-rss-feeds
- Google News RSS query generator
- Reddit collector improvements
- Hacker News advanced collector
- GitHub releases collector
- GitHub trending collector
- YouTube channel RSS collector
- Sitemap collector
- Source health scoring
- Source categories and priorities

### Tech tasks
- Add source discovery scripts
- Add source validation script
- Add duplicate source detection
- Add source failure backoff
- Add automatic disabling of broken sources
- Add source statistics endpoint

## v0.3 — Extraction Quality

Goal: improve article text quality and reduce noise.

### Features
- Per-source extraction strategy
- Better canonical URL extraction
- Better language detection
- Better author/date extraction
- HTML cleanup
- Cookie/banner removal heuristics
- Playwright fallback for selected sources
- Extraction quality dashboard
- Retry failed extraction

### Tech tasks
- Add extractor diagnostics
- Store extractor failure reasons
- Add extraction benchmark dataset
- Add per-source extractor override
- Add raw HTML retention policy

## v0.4 — AI Intelligence

Goal: improve summaries, relevance and semantic capabilities.

### Features
- Better prompts
- Multi-language summaries
- French briefing output
- Entity extraction normalization
- Topic taxonomy
- Personal relevance tuning
- Article novelty score based on cluster size and freshness
- Semantic search endpoint
- Similar articles endpoint
- Trend detection

### Tech tasks
- Add prompt versioning
- Add model configuration UI/env
- Add embedding reprocessing command
- Add AI retry queue
- Add token/time cost tracking

## v0.5 — Dashboard Productization

Goal: make the dashboard useful as a daily news cockpit.

### Features
- Top news page
- Article detail page
- Cluster detail page
- Source health page
- Briefing page
- Search filters
- Read/unread state
- Save/favorite articles
- Hide noisy sources
- Manual reprocess button
- Manual generate briefing button

### Tech tasks
- Improve API schemas
- Add pagination
- Add frontend error states
- Add loading states
- Add simple auth if exposed outside LAN

## v0.6 — Jarvis Integration

Goal: make Helix queryable by Jarvis.

### Features
- /v1/jarvis/query
- Natural language search
- Question answering over recent articles
- Semantic context retrieval
- Source-cited answers
- Daily voice briefing
- Topic-specific briefings
- Alerts for configured topics

### Tech tasks
- Define stable Jarvis API contract
- Add API token support
- Add request/response examples
- Add integration tests
- Add latency budget

## v0.7 — Automation and Alerts

Goal: notify the user when important topics move.

### Features
- Keyword alerts
- Entity alerts
- GitHub repo alerts
- Breaking topic detection
- Telegram/Discord/email alerts
- Weekly recap
- Monthly knowledge digest

### Tech tasks
- Add alerts table
- Add notification worker
- Add notification channels
- Add alert deduplication
- Add quiet hours

## v0.8 — Scale and Reliability

Goal: support large ingestion volume on NAS.

### Features
- Queue retry policy
- Dead-letter queues
- Source backoff
- Worker concurrency controls
- Retention policies
- Backup verification
- Storage cleanup
- Database maintenance
- Metrics dashboard

### Tech tasks
- Add DLQ
- Add retry_count and next_retry_at usage
- Add cleanup worker
- Add Postgres vacuum/analyze docs
- Add MinIO lifecycle docs
- Add Grafana dashboards

## v0.9 — Advanced Research Mode

Goal: turn Helix into a personal research engine.

### Features
- Deep search by topic
- Timeline of an event
- Compare coverage by country/source
- Source bias comparison
- Entity pages
- Company/person/country pages
- Export research note
- Markdown report generation
- RAG over article history

### Tech tasks
- Add research endpoints
- Add report generator
- Add timeline builder
- Add cluster evolution tracking
- Add semantic + full-text hybrid search

## v1.0 — Personal Intelligence OS

Goal: stable personal intelligence platform.

### Features
- Reliable NAS deployment
- Large source registry
- Stable extraction
- Semantic memory
- Daily/weekly/monthly briefings
- Jarvis integration
- Dashboard
- Alerts
- Research mode
- Backup and restore
- Operational monitoring

### Definition of done
- Runs for 30 days without manual intervention
- Handles 500+ sources
- Processes thousands of articles
- Generates daily briefings automatically
- Allows semantic search over history
- Provides source-cited Jarvis answers
