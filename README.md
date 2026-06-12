# 📰 News NAS — Personal Intelligence Platform

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
                        AI Pipeline (Ollama: summarize, classify, embed)
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
- **LLM**: Ollama (local, no API key needed)
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
3. Start Ollama and pull `nomic-embed-text` + `mistral` models
4. Import sources from `awesome-rss-feeds`
5. Start all workers and services

Wait 5-10 minutes for everything to stabilize.

### 4. Access

- **Dashboard**: http://192.168.1.50:${DASHBOARD_PORT:-3000}
- **API Docs**: http://192.168.1.50:8000/docs
- **FreshRSS**: http://192.168.1.50:${FRESHRSS_PORT:-8080}
- **Meilisearch**: http://192.168.1.50:7700
- **MinIO Console**: http://192.168.1.50:9001

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
| Ollama | 11434 | Local LLM (embeddings, summaries) |
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

**Three async workers** consume Redis queues:

1. **collect** — reads sources, calls collectors (RSS, Reddit, GitHub, etc.), inserts raw items
2. **extract** — fetches URLs, extracts full text via morss → trafilatura → news-please → newspaper4k → playwright
3. **ai** — summarizes, classifies, extracts entities, generates embeddings, scores articles

Watch logs:
```bash
docker compose logs -f worker_collect
docker compose logs -f worker_extract
docker compose logs -f worker_ai
```

---

## 🔍 API Endpoints

```bash
# Health check
curl http://192.168.1.50:8000/health

# Get articles
curl http://192.168.1.50:8000/articles?limit=10

# Search
curl http://192.168.1.50:8000/search?q=artificial+intelligence&limit=20

# Get clusters (same event, multiple sources)
curl http://192.168.1.50:8000/clusters

# Get daily briefing
curl http://192.168.1.50:8000/briefings/daily

# Jarvis mode — question answering
curl -X POST http://192.168.1.50:8000/jarvis/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the top AI news today?"}'
```

Full OpenAPI docs: http://192.168.1.50:8000/docs

### v1 Contract (Jarvis / service-to-service)

- `GET /v1/health`
- `POST /v1/jarvis/query`
- `GET /v1/search?q=...`
- `GET /v1/briefings/daily`
- `GET /v1/pipeline/metrics`
- `GET /v1/pipeline/sources-status`

If `REQUIRE_API_TOKEN=true`, provide header:

```bash
X-API-Token: <HELIX_API_TOKEN>
```

---

## 🎯 Features

- ✅ **35+ RSS sources** preconfigured (tech, AI, supply chain, pharma, geopolitics)
- ✅ **Multi-language** (FR/EN) — Google News RSS auto-queries
- ✅ **Full-text extraction** — 6-layer fallback chain for high success rate
- ✅ **Local LLM** — Ollama: summaries, classification, entity extraction, embeddings
- ✅ **Semantic search** — pgvector + IVF index for fast similarity
- ✅ **Event clustering** — auto-groups articles about the same event
- ✅ **Personal scoring** — rank articles by your interests
- ✅ **Daily briefings** — automated newsletter generation
- ✅ **Jarvis integration** — answer natural language questions
- ✅ **Versioned API contract** — `/v1/*` endpoints for Jarvis and other clients
- ✅ **Operational visibility** — pipeline metrics and source status endpoints
- ✅ **All data local** — nothing leaves your NAS

---

## 📦 Importing More Sources

```bash
# Clone awesome-rss-feeds and parse OPML files
python scripts/import_awesome_feeds.py --output config/sources.yaml --limit 500
```

Then restart `worker_collect`:
```bash
docker compose restart worker_collect
```

---

## 🔐 Security Notes

- All services listen on localhost only (or your NAS IP)
- No credentials sent anywhere (Ollama is local)
- Meilisearch has a master key — set it in `.env`
- PostgreSQL password should be strong
- MinIO (S3-like) has separate root key

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
```

**Ollama models not downloaded?**
```bash
docker compose exec ollama ollama list
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama pull mistral
```

**Out of disk space?**
```bash
docker system prune -a --volumes
du -sh data/*
```

---

## 📚 Further Reading

- [Trafilatura](https://trafilatura.readthedocs.io) — extraction
- [Ollama](https://ollama.ai) — local LLM
- [Meilisearch](https://meilisearch.com/docs) — search
- [FastAPI](https://fastapi.tiangolo.com) — API
- [Next.js 14](https://nextjs.org) — frontend

---

## 📄 License

MIT

---

Made with ❤️ for personal intelligence.
