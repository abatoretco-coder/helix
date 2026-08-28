# Helix Roadmap

## Product Direction

Helix is being built as a local-first news intelligence system for a NAS: it should ingest reliably, extract clean text, enrich it with AI, and expose the result through a cockpit that is useful every day.

For the current repository audit, applied fixes, and execution-focused roadmap, see [Repository Analysis and Applied Roadmap](REPOSITORY_ANALYSIS_AND_ROADMAP.md).

### Guiding principles
- Local-first by default for ingestion, storage, and default news summaries; OpenAI usage must stay explicit, endpoint-triggered, and budgeted.
- Reliability before breadth: every new source or AI feature must preserve end-to-end stability.
- Measurable improvements only: each milestone should have a visible operational or product gain.
- Prefer small composable services and queues over tightly coupled monolith logic.
- Keep a clear path from raw item to article, cluster, briefing, and queryable history.

### Release gates
- A milestone ships only if the pipeline still starts, processes, and produces observable outputs.
- Every new feature must be covered by at least one verification path: smoke test, API check, or manual operator flow.
- Operational changes must be reflected in docs or validation scripts in the same iteration.

### Current sequencing
1. Stabilize the local pipeline.
2. Expand source coverage.
3. Improve extraction quality.
4. Upgrade AI relevance and search.
5. Productize the dashboard.
6. Make the system queryable by Jarvis.
7. Add alerts and automation.
8. Harden the stack for scale and retention.
9. Turn the archive into a research engine.
10. Freeze the platform into a personal intelligence OS.

## v0.1 — MVP Stabilization

Goal: make the local NAS pipeline reliable end-to-end.

What success looks like:
- Fresh articles move from source to storage without manual intervention.
- A daily briefing can be generated from the latest data.
- Operators can verify the stack quickly after a restart or deployment.

Dependencies:
- PostgreSQL, Redis, MinIO, MeiliSearch, and optional OpenAI API access for explicit AI features.
- Core workers for extraction, AI, clustering, and briefing.

### Features
- Stable Docker Compose stack
- RSS + Google News RSS collection
- Full-text extraction with fallback chain
- PostgreSQL + pgvector storage
- MinIO raw storage
- Meilisearch indexing
- OpenAI-compatible summarization and embeddings when `BACKGROUND_AI_ENABLED=true`
- Per-endpoint OpenAI usage counters and budget controls
- Cluster generation
- Daily briefing generation
- Basic FastAPI endpoints
- Basic dashboard

### Tech tasks
- Embed daily scheduler in worker_briefing
- Improve smoke tests
- Improve Docker dependencies
- Improve briefing date fallback
- Add MVP closure checklist
- Add backup/restore verification

### Exit criteria
- Compose boots without broken runtime dependencies.
- The smoke test verifies the main pipeline endpoints and worker services.
- A fresh install can produce at least one briefing and one cluster run.

## v0.2 — Source Expansion

Goal: increase coverage and source diversity.

What success looks like:
- The system can ingest from both broad feeds and targeted sources.
- Broken sources are measurable, isolated, and eventually disabled.

Dependencies:
- Source discovery scripts.
- Health scoring and backoff logic.

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

### Exit criteria
- Duplicate sources are identified before they pollute the pipeline.
- Operators can see which sources are failing and why.
- Source expansion increases coverage without causing a large jump in noise.

## v0.3 — Extraction Quality

Goal: improve article text quality and reduce noise.

What success looks like:
- Fewer empty or broken articles.
- Cleaner article bodies with better source attribution.
- Selected hard sources fall back to Playwright only when needed.

Dependencies:
- Per-source strategy metadata.
- Extraction diagnostics and retention policy.

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

### Exit criteria
- Extraction failures are explainable, not just counted.
- The user can tune extraction behavior per source.
- The raw HTML retention policy is explicit and documented.

## v0.4 — AI Intelligence

Goal: improve summaries, relevance and semantic capabilities.

What success looks like:
- Articles are ranked and summarized in a way that reflects the user's interests.
- Search becomes semantic enough to be useful over the archive.
- Cluster novelty and trend signals improve daily triage.

Dependencies:
- Stable embeddings model selection.
- Entity normalization and prompt versioning.

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

### Exit criteria
- Summaries and scores are reproducible enough to debug.
- Semantic search returns relevant results on historical data.
- Personal relevance scoring can be tuned from a profile file or environment config.

## v0.5 — Dashboard Productization

Goal: make the dashboard useful as a daily news cockpit.

What success looks like:
- A user can start the day from the dashboard and understand what needs attention.
- Cluster, briefing, source, and article views feel like one product.

Dependencies:
- Stable API schemas.
- Basic auth if the dashboard is exposed beyond the LAN.

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

### Exit criteria
- The cockpit exposes the main operational state without extra navigation.
- Manual reprocess and generate actions exist and are safe to trigger.
- The main views have a clear path from list to detail.

## v0.6 — Jarvis Integration

Goal: make Helix queryable by Jarvis.

What success looks like:
- Jarvis can ask natural-language questions over recent and historical articles.
- Answers cite sources and stay within a controlled latency budget.

Dependencies:
- Stable API contract.
- Semantic retrieval over articles and clusters.

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

### Exit criteria
- Requests are authenticated when required.
- Answers are source-backed and consistent enough to trust.
- The latency budget is documented and tested.

## v0.7 — Automation and Alerts

Goal: notify the user when important topics move.

What success looks like:
- Important shifts surface proactively instead of waiting for manual checks.
- Alerts are deduplicated and respectful of quiet hours.

Dependencies:
- Alerts table.
- Notification transport and scheduling.

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

### Exit criteria
- Alert rules are persistent and inspectable.
- Duplicate notifications are suppressed.
- Quiet hours are honored across transports.

## v0.8 — Scale and Reliability

Goal: support large ingestion volume on NAS.

What success looks like:
- The system can absorb bursts of ingestion without collapsing.
- Storage and database maintenance become routine rather than ad hoc.

Dependencies:
- Retry and DLQ semantics.
- Retention and cleanup policies.

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
- Extend cleanup worker coverage beyond logs and stale failed/duplicate raw items
- Add Postgres vacuum/analyze docs
- Add MinIO lifecycle docs
- Add Grafana dashboards

### Exit criteria
- Failed jobs can be retried or quarantined intentionally.
- Cleanup and maintenance are documented and repeatable.
- Metrics are sufficient to spot backlog growth before it hurts UX.

## v0.9 — Advanced Research Mode

Goal: turn Helix into a personal research engine.

What success looks like:
- A topic can be explored over time with context, source mix, and evolution.
- The archive can be used to produce structured research notes.

Dependencies:
- Hybrid semantic + full-text search.
- Timeline and report generation primitives.

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

### Exit criteria
- Event timelines are reproducible from the historical archive.
- Research exports are good enough to reuse outside the app.
- Coverage and bias can be compared at source and country level.

## v1.0 — Personal Intelligence OS

Goal: stable personal intelligence platform.

What success looks like:
- Helix runs for long stretches with minimal maintenance.
- The data it produces is reliable enough to depend on daily.
- The platform feels complete across ingestion, intelligence, operations, and research.

Dependencies:
- Mature retry and maintenance behavior.
- Stable dashboard, alerts, briefings, and Jarvis integration.

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

### Operational guardrails
- Backup and restore must be proven, not assumed.
- Core flows must remain observable after upgrades.
- New source additions should not require code changes for every case.
