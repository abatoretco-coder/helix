# 📰 Helix — Personal Intelligence Platform

A self-hosted news aggregation, extraction, and AI-powered intelligence platform running on your NAS.

Collects RSS/web sources → extracts full text → stores embeddings → generates summaries & rankings → exposes via dashboard + API.

---

## ⚙️ Architecture

```
RSS/APIs → Collectors → Raw Items (Redis queue)
                            ↓
                        Extraction (trafilatura, news-please, newspaper4k)
                            ↓
                        Articles + MinIO storage
                            ↓
                        AI Pipeline (OpenAI-compatible provider when enabled)
                            ↓
                        Scoring + Meilisearch index
                            ↓
                        FastAPI + Next.js Dashboard
```

**Stack:**
- **Data**: PostgreSQL + pgvector (semantic search)
- **Queue**: Redis
- **Storage**: MinIO (raw HTML/JSON)
- **Search**: Meilisearch
- **LLM**: OpenAI-compatible provider for opt-in AI jobs; local extractive news summaries by default; Ollama service included for local model runtime work
- **API**: FastAPI
- **Frontend**: Next.js 14
- **Extraction**: morss → trafilatura → news-please → newspaper4k → playwright

---

## 🚀 Quick Start

### Prerequisites
- Docker + Docker Compose v2
- `docker`, `docker-compose` commands available
- 192.168.1.50 IP accessible (or change `NAS_IP` in `.env`)
- ~10GB free space on NAS

### 1. Clone or Download

```bash
cd /mnt/nas/volume1  # or wherever on your NAS
git clone <repo-url> helix
cd helix
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and set your NAS IP + passwords
nano .env
```

### 3. Deploy

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

This will:
1. Build Docker images
2. Start PostgreSQL, Redis, MinIO, Meilisearch
3. Skip Ollama by default
4. Import sources from `awesome-rss-feeds`
5. Start all core workers and services

Wait 5-10 minutes for everything to stabilize.

### 4. Access

- **Dashboard**: http://192.168.1.50:${DASHBOARD_PORT:-3000}
- **API Docs**: http://192.168.1.50:8000/docs
- **FreshRSS**: http://192.168.1.50:${FRESHRSS_PORT:-8080}
- **Meilisearch**: http://192.168.1.50:7700
- **MinIO Console**: http://192.168.1.50:9001
- **Prometheus**: http://192.168.1.50:${PROMETHEUS_PORT:-19090}

---

## 📖 Services

| Service | Port | Role |
|---------|------|------|
| PostgreSQL | `${POSTGRES_PORT:-5432}` | Articles, metadata |
| Redis | `${REDIS_PORT:-6379}` | Queue for workers |
| MinIO | 9000/9001 | Raw HTML/JSON storage |
| Meilisearch | 7700 | Full-text search |
| FreshRSS | `${FRESHRSS_PORT:-8080}` | RSS cockpit + UI |
| morss | 8081 | RSS enrichment proxy |
| Ollama | 11434 | Shared local runtime on `jarvis_ai_runtime` (`ollama-central`) |
| API | 8000 | FastAPI backend |
| Dashboard | `${DASHBOARD_PORT:-3000}` | Next.js frontend |

---

## 🔧 Configuration

### Sources
Edit or create `config/sources.yaml`:

```yaml
sources:
  - name: "Hacker News"
    type: rss
    url: https://news.ycombinator.com/rss
    category: tech
    priority: 1          # 1=highest (refresh every 15 min)
    enabled: true

  - name: "AI Google News"
    type: google_news_rss
    query: "artificial intelligence"
    language: en
    priority: 1

  - name: "Reddit LocalLLaMA"
    type: reddit
    subreddit: LocalLLaMA
    category: ai
    priority: 2
```

### Scoring Rules
`config/scoring_rules.yaml` — weights for article ranking:
- Topic interest (keywords you care about)
- Source reliability
- Freshness
- Quality of extraction

### LLM Prompts
`config/llm_prompts.yaml` — customize summarization, classification, entity extraction prompts.

---

## 🔄 Workers

**Six async workers** handle collection, enrichment, briefing, and retention:

1. **collect** — reads sources, calls collectors (RSS, Reddit, GitHub, etc.), inserts raw items
2. **extract** — fetches URLs, extracts full text via morss → trafilatura → news-please → newspaper4k → playwright
3. **ai** — summarizes, classifies, extracts entities, generates embeddings, scores articles
4. **cluster** — consumes `queue:cluster` and groups semantically similar articles
5. **briefing** — consumes `queue:briefing`, generates daily markdown briefings, and runs the embedded daily scheduler trigger (no dedicated scheduler container)
6. **cleanup** — runs periodic retention tasks for old processing logs and stale failed/duplicate raw items

Watch logs:
```bash
docker compose logs -f worker_collect
docker compose logs -f worker_extract
docker compose logs -f worker_ai
docker compose logs -f worker_cluster
docker compose logs -f worker_briefing
docker compose logs -f worker_cleanup
```

Dev validation:
```bash
./scripts/dev_check.sh
```

Static-only validation without running containers:

```bash
STATIC_ONLY=true ./scripts/dev_check.sh
```

On Windows/PowerShell:

```powershell
.\scripts\dev_check.ps1 -StaticOnly
```

---

## 🔍 API Endpoints

```bash
# Health check
curl http://192.168.1.50:8000/health

# Get articles
curl http://192.168.1.50:8000/articles?limit=10

# Get semantically similar articles
curl http://192.168.1.50:8000/articles/123/similar?limit=10

# Search
curl http://192.168.1.50:8000/search?q=artificial+intelligence&limit=20

# Semantic search via pgvector/provider embeddings
curl http://192.168.1.50:8000/search/semantic?q=artificial+intelligence&limit=20

# Get clusters (same event, multiple sources)
curl http://192.168.1.50:8000/clusters

# Get daily briefing
curl http://192.168.1.50:8000/briefings/daily

# Get fresh news items selected for a Jarvis/client view
curl "http://192.168.1.50:8000/v1/news/items?geoFilter=france&view=breaking&limit=20"

# Generate a short news summary from selected items
# Defaults to local extractive bullets. Set NEWS_SUMMARY_PROVIDER=openai to use OpenAI.
curl -X POST http://192.168.1.50:8000/v1/news/summary \
  -H "Content-Type: application/json" \
  -d '{"scopeLabel":"France","items":[{"title":"Example 1"},{"title":"Example 2"},{"title":"Example 3"}]}'

# Jarvis mode — question answering
curl -X POST http://192.168.1.50:8000/jarvis/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the top AI news today?"}'
```

Full OpenAPI docs: http://192.168.1.50:8000/docs

### v1 Contract (Jarvis / service-to-service)

- `GET /v1/health`
- `GET /v1/agent/capabilities`
- `GET /v1/agent/context`
- `POST /v1/agent/memories`
- `POST /v1/agent/tasks`
- `POST /v1/agent/tasks/claim`
- `POST /v1/jarvis/query`
- `GET /v1/news/items`
- `POST /v1/news/summary`
- `GET /v1/ops/openai-usage`
- `GET /v1/articles/{article_id}/similar`
- `GET /v1/search?q=...`
- `GET /v1/search/semantic?q=...`
- `GET /v1/briefings/daily`
- `GET /v1/pipeline/metrics`
- `GET /v1/pipeline/sources-status`
- `GET /v1/sources/recommendations`
- `GET /v1/queues/dead`
- `GET /v1/ops/summary`

If `REQUIRE_API_TOKEN=true`, provide header:

```bash
X-API-Token: <HELIX_API_TOKEN>
```

Dashboard calls to `/v1` can forward the same token with:

```bash
NEXT_PUBLIC_HELIX_API_TOKEN=<HELIX_API_TOKEN>
```

LAN note: this is acceptable for local NAS-only usage. Do not expose a public dashboard with this token in browser-delivered env vars. For external exposure, add server-side auth.

Optional dashboard Basic Auth can be enabled with:

```bash
DASHBOARD_BASIC_AUTH_ENABLED=true
DASHBOARD_BASIC_AUTH_USER=helix
DASHBOARD_BASIC_AUTH_PASSWORD=<strong-password>
```

Additional NAS intelligence endpoints:

- `GET /v1/queues/dead/{queue_name}`
- `POST /v1/queues/dead/{queue_name}/retry`
- `POST /v1/queues/dead/{queue_name}/purge`
- `GET /v1/watchlist`
- `GET /v1/watchlist/matches`
- `GET /v1/projects`
- `GET /v1/projects/{slug}/articles`
- `GET /v1/inbox`
- `GET /v1/clusters/{cluster_id}/timeline`
- `POST /v1/home-assistant/briefing-ready`
- `POST /v1/home-assistant/alert`

---

## 🎯 Features

- ✅ **295 curated sources** preconfigured, including 94 French-language sources
- ✅ **Multi-language** (FR/EN + international) — direct feeds and Google News RSS auto-queries
- ✅ **Full-text extraction** — 6-layer fallback chain for high success rate
- ✅ **Opt-in AI pipeline** — OpenAI-compatible summaries, classification, entity extraction, and embeddings when `BACKGROUND_AI_ENABLED=true`
- ✅ **Local-first news summary API** — extractive bullets by default, optional OpenAI-compatible provider when explicitly enabled
- ✅ **Semantic search** — pgvector + IVF index for fast similarity
- ✅ **Similar articles** — article-to-article recommendations from embeddings
- ✅ **Event clustering** — auto-groups articles about the same event
- ✅ **Personal scoring** — rank articles by your interests
- ✅ **Daily briefings** — automated newsletter generation
- ✅ **Jarvis integration** — answer natural language questions
- ✅ **Agent API** — structured context and durable memory writeback for external agents
- ✅ **Versioned API contract** — `/v1/*` endpoints for Jarvis and other clients
- ✅ **Operational visibility** — pipeline metrics and source status endpoints
- ✅ **Local-first data flow** — ingestion, storage, embeddings, and default news summaries stay on your NAS; optional external summary providers are opt-in

---

## 📦 Importing More Sources

```bash
# Append the curated French-first enrichment pack
python scripts/enrich_sources.py --dry-run
python scripts/enrich_sources.py

# Clone awesome-rss-feeds and parse OPML files
python scripts/import_awesome_feeds.py --output config/sources.yaml --limit 500

# Validate source shape and duplicates
python scripts/validate_sources.py --strict

# Review freshness, cadence, and coverage recommendations
python scripts/source_realtime_plan.py --top 20
```

Then restart `worker_collect`:
```bash
docker compose restart worker_collect
```

See [Source enrichment](docs/SOURCE_ENRICHMENT.md) for coverage details and database sync notes.
See [News real-time and quality roadmap](docs/NEWS_REALTIME_QUALITY_ROADMAP.md) for the freshness plan.

---

## 🔐 Security Notes

- All services listen on localhost only (or your NAS IP)
- OpenAI is not used in shadow/background mode by default. Keep `BACKGROUND_AI_ENABLED=false` to prevent article-ingestion AI calls.
- Explicit OpenAI calls are persisted in `/v1/ops/openai-usage`; set `OPENAI_*_REQUEST_LIMIT` before granting a key to a client with frequent queries.
- No news summary content leaves the NAS by default. `/v1/news/summary` uses local extractive bullets unless `NEWS_SUMMARY_PROVIDER=openai` is set.
- When `NEWS_SUMMARY_PROVIDER=openai`, selected titles/snippets submitted to `/v1/news/summary` are sent to the configured OpenAI-compatible endpoint.
- Jarvis answers and semantic search can call OpenAI only when their endpoints are explicitly requested and `OPENAI_API_KEY` is configured.
- Meilisearch has a master key — set it in `.env`
- PostgreSQL password should be strong
- MinIO (S3-like) has separate root key
- PostgreSQL, Redis, MinIO, Meilisearch, morss, and Prometheus bind to `127.0.0.1` by default; only expose a service deliberately through a reverse proxy or a dedicated bind setting.

## 🗃️ Database Migrations (Alembic)

Run schema migrations with the API container environment:

```bash
./scripts/db_migrate.sh
```

This executes:

```bash
docker compose exec -T api alembic upgrade head
```

## 📈 Observability

- Prometheus-compatible metrics endpoint: `GET /metrics`
- Prometheus server: `http://<NAS_IP>:${PROMETHEUS_PORT:-19090}`
- Operational JSON endpoints:
  - `GET /v1/pipeline/metrics`
  - `GET /v1/pipeline/sources-status`

### Grafana (existing NAS instance)

1. Add Prometheus datasource in Grafana pointing to:

```text
http://<NAS_IP>:${PROMETHEUS_PORT:-19090}
```

2. Import the dashboard JSON:

```bash
GRAFANA_URL=http://<grafana-host>:3000 \
GRAFANA_TOKEN=<service-account-token> \
./scripts/import_grafana_dashboard.sh
```

Dashboard file:

```text
monitoring/grafana/helix-news-overview.json
```

## 💾 Backup / Restore

```bash
# Backup PostgreSQL
./scripts/db_backup.sh

# Restore PostgreSQL
./scripts/db_restore.sh backups/newsdb_YYYYMMDD_HHMMSS.sql.gz
```

To expose safely over the internet, use a reverse proxy (Nginx, Traefik) with:
- Rate limiting
- Authentication (basic auth, OAuth2)
- TLS/HTTPS

---

## 🐛 Troubleshooting

**API not responding?**
```bash
docker compose logs api
docker compose ps
```

**Workers stuck?**
```bash
docker compose restart worker_collect
docker compose restart worker_extract
docker compose restart worker_ai
docker compose restart worker_cluster
docker compose restart worker_briefing
```

**Ollama local runtime?**

Helix réutilise le runtime commun exposé sous `ollama-central` sur le réseau
Docker externe `jarvis_ai_runtime`. Il ne démarre pas un second Ollama et ne
télécharge aucun modèle pendant son déploiement.

**Out of disk space?**
```bash
docker system prune -a --volumes
du -sh data/*
```

---

## 📚 Further Reading

- [Repository analysis and applied roadmap](docs/REPOSITORY_ANALYSIS_AND_ROADMAP.md)
- [Agent API architecture](docs/AGENT_API_ARCHITECTURE.md)
- [Trafilatura](https://trafilatura.readthedocs.io) — extraction
- [Ollama](https://ollama.ai) — local model runtime
- [Meilisearch](https://meilisearch.com/docs) — search
- [FastAPI](https://fastapi.tiangolo.com) — API
- [Next.js 14](https://nextjs.org) — frontend

---

## 📄 License

MIT

---

Made with ❤️ for personal intelligence.
