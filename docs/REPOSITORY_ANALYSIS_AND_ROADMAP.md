# Helix Repository Analysis and Applied Roadmap

Last reaudit: 2026-08-16. See [Repository reaudit 2026-08-16](REPOSITORY_REAUDIT_2026-08-16.md) for the applied freshness, AI cost-control, migration, and network-exposure corrections.

## Current product shape

Helix is a local-first NAS intelligence platform:

- Ingestion: YAML/DB sources feed RSS, Google News RSS, Reddit, Hacker News, GitHub trending, and YouTube collectors.
- Processing: Redis queues drive extract, AI, cluster, briefing, and cleanup workers.
- Storage: PostgreSQL/pgvector stores normalized entities, MinIO keeps raw artifacts, Meilisearch supports keyword search.
- Intelligence: OpenAI-compatible AI can generate summaries, embeddings, scoring, categories, watchlist and research-project matching when enabled; local model runtime work is parked unless suitable hardware becomes available.
- Product surfaces: FastAPI exposes raw and `/v1` contract endpoints; Next.js provides dashboard, source health, operations, inbox, watchlist, projects, clusters, search, briefings, articles, and Jarvis.
- Operations: Prometheus metrics, dead-letter queue inspection/retry/purge, backup/restore scripts, Obsidian export, and cleanup retention worker are present.

## Important findings

- Schema state had drifted between fresh-install SQL, Alembic migrations, and SQLAlchemy metadata. Productization tables now exist in fresh SQL and Alembic, with a follow-up migration for missing defaults/indexes.
- Dashboard linting existed as a script but was not configured, so `dev_check.sh` could enter an interactive Next.js prompt. ESLint is now configured and clean.
- Python dead-code checks were not automated. Ruff is now configured and wired into `dev_check.sh` when installed.
- The source registry was heavily English-skewed: 184 sources total, with only 8 French-language entries. A curated French-first enrichment pack now raises this to 275 total sources and 79 French-language entries.
- Source health existed but lacked enough signal for operating a 275-source registry. It now includes 24h/7d volume, conversion, success, quality, language mismatch, health score, quality band, and diagnostics.
- Source quality metrics now produce actionable maintenance recommendations so the registry can be tuned continuously instead of inspected manually.
- External agents need a stable contract rather than scraping dashboard/API internals. `/v1/agent/*` now provides context bundles and durable memory writeback for Jarvis-style clients.
- Jarvis-style agents also need persistent work, not only request/response calls. Agent tasks now provide a durable queued/running/done/failed lifecycle.
- The new news product endpoints are useful for Jarvis but had a local-first documentation gap: `/v1/news/summary` defaulted to OpenAI while README still claimed that no data leaves the NAS. The endpoint now defaults to local extractive bullets and exposes OpenAI as explicit opt-in via `NEWS_SUMMARY_PROVIDER=openai`.
- The worker/API AI implementation is currently OpenAI-compatible. OpenAI usage must stay explicit: `BACKGROUND_AI_ENABLED=false` by default, local news summaries by default, and endpoint-triggered calls only when a user/client requests them.
- `.env.example` duplicated `OPENAI_API_KEY`, increasing configuration ambiguity. It now has one OpenAI key entry plus dedicated news-summary provider/model/timeout settings.
- The docs still described five workers while Compose includes `worker_cleanup`. README, architecture docs, backlog, roadmap, checklist, and smoke test now reflect six workers.
- Runtime smoke tests require live containers; static validation can now be run with `STATIC_ONLY=true`.
- `npm audit` still reports Next/PostCSS advisories. The proposed automatic fix is a breaking upgrade to Next 16, so it remains an explicit roadmap item rather than a blind change.
- See [Next.js Security Upgrade Plan](NEXT_SECURITY_UPGRADE_PLAN.md) for the safe migration path.

## Corrections already applied

- Added Alembic migration `20260627_01_align_productization_schema.py`.
- Aligned API and worker SQLAlchemy models with entity mention indexes and `briefings.period_date` date semantics.
- Added ESLint configuration and matching Next 14 lint dependencies.
- Removed obvious Python and dashboard dead code found by Ruff/ESLint.
- Updated `scripts/smoke_test.sh` to assert `worker_cleanup`.
- Updated `scripts/dev_check.sh` with optional Ruff checks and `STATIC_ONLY=true`.
- Updated docs to reflect cleanup worker, productization tables, and current migration TODOs.
- Added `scripts/dev_check.ps1` for Windows/PowerShell static validation.
- Extended cleanup retention to MinIO raw HTML/JSON objects and record per-run object deletion counts.
- Added `/articles/{article_id}/similar` and dashboard article-detail recommendations backed by pgvector embeddings.
- Added `/search/semantic` and dashboard semantic search mode backed by pgvector/provider embeddings.
- Added optional dashboard Basic Auth middleware.
- Added `raw_items.next_retry_at` with scheduled extraction retry backoff.
- Added `scripts/enrich_sources.py`, appended 91 curated sources, and documented the enrichment workflow in `docs/SOURCE_ENRICHMENT.md`.
- Extended `/sources/health` and the dashboard Sources page into a full source-quality cockpit with filters, health ranking, quality bands, and source actions.
- Added `/sources/recommendations` and dashboard recommended actions for disabling broken feeds, refreshing stale feeds, changing priority, reviewing language metadata, and monitoring errors.
- Added `/agent/capabilities`, `/agent/context`, `/agent/memories`, a Python SDK, and an example Jarvis Docker container template.
- Added `/agent/tasks` lifecycle endpoints plus SDK helpers for create/list/claim/complete/fail/cancel task flows.
- Added local-first `/v1/news/items` and `/v1/news/summary` documentation for Jarvis/client product responses.
- Changed `/v1/news/summary` to use local extractive summaries by default and report `summaryProvider` in the response.
- Added `news_items_supported`, `news_summary_supported`, and `news_summary_provider` to `/v1/agent/capabilities`.
- Added dedicated `NEWS_SUMMARY_PROVIDER`, `NEWS_SUMMARY_MODEL`, and `NEWS_SUMMARY_TIMEOUT_SECONDS` deployment settings.
- Made Ollama opt-in in `scripts/deploy.sh` with `INSTALL_OLLAMA=true`; default NAS deployments no longer start or pull Ollama models.
- Updated `scripts/smoke_test.sh` so Ollama is only required when `INSTALL_OLLAMA=true`.
- Added `scripts/source_realtime_plan.py`, 20 near-real-time Google News radars, and `docs/NEWS_REALTIME_QUALITY_ROADMAP.md`.
- Added collect worker cadence controls for active/idle sleep and optional max due sources per cycle.

## Roadmap

### Phase 0: Repository hygiene, applied now

- Keep Python import/dead-code checks green with Ruff.
- Keep dashboard ESLint and production build green.
- Keep docs aligned with Compose services, queues, and schema.
- Maintain static validation path independent of running containers.

### Phase 1: Runtime closure

- Boot the full Docker stack and run `scripts/smoke_test.sh`.
- Run `scripts/db_migrate.sh` against an existing DB, then verify schema parity with fresh `init_db.sql`.
- Add an automated smoke result section to `docs/MVP_CLOSURE_CHECKLIST.md`.
- Decide whether non-`/v1` mutating endpoints should remain open on LAN or require auth.
- Exercise `/v1/news/items` and `/v1/news/summary` against live NAS data once the Docker stack is available.

### Phase 2: Security and dependency hardening

- Plan and test the Next.js upgrade path that resolves current `npm audit` advisories; initial plan documented in `NEXT_SECURITY_UPGRADE_PLAN.md`.
- Add a documented dashboard auth strategy before exposing the UI beyond LAN.
- Add secret-rotation instructions for PostgreSQL, MinIO, Meilisearch, and `HELIX_API_TOKEN`.
- Add non-fatal dependency audit reporting to CI/dev checks once the Next upgrade path is chosen.
- Keep OpenAI usage opt-in per feature and document exactly which payload fields can leave the NAS.
- Add usage counters/cost telemetry for OpenAI calls before enabling any background AI in production.

### Phase 3: Data lifecycle and reliability

- [x] Extend cleanup beyond DB rows to raw HTML/JSON objects in MinIO.
- [x] Add scheduled retry backoff with `raw_items.next_retry_at`.
- [x] Enrich the source registry with a reusable French-first curated pack.
- [x] Add per-source quality scoring and dashboard triage for the expanded registry.
- [x] Add static source freshness planning and near-real-time radar expansion.
- Record structured retention job details for deleted object counts and failure reasons.
- Add Grafana panels for queue depth, DLQ depth, extraction failure rate, and cleanup results.

### Phase 4: Intelligence quality

- Add source-cited Jarvis answers with stable citation payloads.
- Add citation payloads to `/v1/news/summary` so agent answers can reference the selected articles directly.
- [x] Add similar-articles endpoint over pgvector.
- [x] Add dedicated semantic-search endpoint over pgvector.
- Normalize entities before watchlist/research matching.
- Add French briefing generation mode and prompt versioning.
- Keep Ollama provider work parked unless local hardware becomes available.
- Add explicit per-endpoint OpenAI budget limits for Jarvis, semantic search, and news summaries.
- Add one-click replacement sourcing for stale/noisy feeds by proposing better direct RSS or Google News query alternatives.

### Phase 5: Product surface

- Add cluster detail/timeline route if the current inline cluster view becomes too dense.
- [x] Add dashboard controls for saved/read/hidden state outside the inbox.
- Add source import/export UI for OPML.
- Add alert rule management and notification channel testing in the dashboard.
- [x] Add a stable agent API and client library for Jarvis integration.
- [x] Add persistent agent task queue semantics for Jarvis work orchestration.

## Validation commands

```bash
STATIC_ONLY=true ./scripts/dev_check.sh
python scripts/enrich_sources.py --dry-run
python scripts/validate_sources.py --strict
npm --prefix dashboard run build
npm --prefix dashboard run audit:prod
docker compose up -d --build
./scripts/db_migrate.sh
./scripts/smoke_test.sh
```

On Windows/PowerShell:

```powershell
.\scripts\dev_check.ps1 -StaticOnly
npm --prefix dashboard run build
```
