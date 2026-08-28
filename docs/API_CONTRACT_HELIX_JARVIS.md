# Contrat API Helix <-> Jarvis

Date: 2026-06-12
Version cible: v1 (implemented)

## 1) Principes
- Helix expose un backend news independant du frontend.
- Jarvis est un client consommateur du contrat.
- Les schemas de reponse doivent rester stables et versionnes.

## 2) Endpoints disponibles aujourd'hui
- GET /health
- GET /articles
- GET /search
- GET /clusters
- GET /briefings/daily
- POST /jarvis/query
- GET /v1/health
- POST /v1/jarvis/query
- GET /v1/news/items
- POST /v1/news/summary
- GET /v1/search
- GET /v1/briefings/daily
- GET /v1/pipeline/metrics
- GET /v1/pipeline/sources-status
- POST /v1/contract/profiles/upsert
- GET /v1/contract/profiles/{profile_id}
- POST /v1/contract/feedback
- GET /v1/contract/feedback/{profile_id}

## 3) Contrat minimal recommande v1

### 3.1 Health
GET /v1/health
- 200: {"status":"ok","service":"helix-api"}

### 3.2 Query conversationnelle
POST /v1/jarvis/query
Request:
{
  "query": "What are the top AI updates today?",
  "date_range": "today|week|month|all",
  "categories": ["ai","tech"],
  "limit": 10,
  "profile": "jarvis_default"
}
Response:
{
  "query": "...",
  "answer": "...",
  "articles": [
    {
      "id": 123,
      "title": "...",
      "url": "...",
      "published_at": "...",
      "summary": "...",
      "category": "...",
      "score": 0.91,
      "distance": 0.11
    }
  ],
  "trace": {
    "model": "mistral",
    "embed_model": "nomic-embed-text",
    "sources_used": 10
  }
}

### 3.3 Recherche brute
GET /v1/search?q=...&limit=20&category=ai

### 3.4 Briefing
GET /v1/briefings/daily?profile=jarvis_default

### 3.5 Actualite selectionnee
GET /v1/news/items?geoFilter=france&tab=france&sectors=economy,defense&view=standard&limit=30

`view=breaking` restricts results to priority-1 sources. It never falls back to unrelated articles when no breaking item is available.

Response:
{
  "status": "ok",
  "source": "helix",
  "generatedAt": "...",
  "freshness": {
    "candidateCount": 42,
    "selectedCount": 30,
    "newestItemAt": "...",
    "oldestItemAt": "...",
    "newestItemAgeMinutes": 18.2,
    "targetMaxAgeMinutes": 240,
    "stale": false,
    "warning": null
  },
  "items": [
    {
      "title": "...",
      "link": "...",
      "source": "...",
      "snippet": "...",
      "publishedAt": "..."
    }
  ]
}

Modes supported: `search`, `briefing`, `watchlist`, `project`, `dashboard`.
The response includes `provider`, `source_count`, an answer generated only
from selected sources, and a separate `sources` array for traceability.

For a dashboard synthesis, provide the already-selected summaries rather than
the raw feed:

```json
{
  "query": "Quels risques dois-je surveiller ?",
  "mode": "dashboard",
  "language": "fr",
  "dashboard_items": [
    {"title": "...", "summary": "...", "source": "...", "url": "...", "score": 0.91}
  ]
}
```

### 3.6 Synthese actualite
POST /v1/news/summary

Request:
{
  "scopeKey": "france",
  "scopeLabel": "France",
  "sectorLabel": "Economie",
  "contextFacts": ["..."],
  "items": [
    {"title": "...", "link": "...", "source": "...", "snippet": "...", "publishedAt": "..."}
  ]
}

Response:
{
  "status": "ok",
  "source": "helix",
  "summaryProvider": "local",
  "scopeKey": "france",
  "text": "- ...",
  "contextNote": "...",
  "selection": {"received": 12, "selected": 12},
  "citations": [
    {"index": 1, "title": "...", "source": "...", "link": "...", "publishedAt": "..."}
  ],
  "generatedAt": "..."
}

The configured provider (currently Ollama) transforms selected titles/snippets into concise bullets. The response always returns the cited selection separately.

### 3.7 Usage OpenAI explicite
GET /v1/ops/openai-usage?days=30

Returns persisted request and token totals by endpoint, operation, model, and outcome. Only remote calls initiated by an API request are recorded. Limits use `OPENAI_*_REQUEST_LIMIT`; `0` disables a given cap.

## 4) Extension contrat recommandee
- POST /v1/contract/profiles/upsert (preferences utilisateur)
- POST /v1/contract/feedback (signal explicite: utile/pas utile)
- GET /v1/pipeline/sources-status (sante ingestion)
- GET /v1/pipeline/metrics (lag + volumes)
- GET /v1/news/items and POST /v1/news/summary (agent-ready news product response)

## 5) Exigences non-fonctionnelles
- Auth service-to-service (token interne X-API-Token implemente)
- Correlation ID par requete
- Timeouts stricts et retries bornes
- Versionnage contractuel explicite (/v1)

## 6) Auth contractuelle v1
- Variables:
  - REQUIRE_API_TOKEN=true|false
  - HELIX_API_TOKEN=<secret>
- Header attendu quand REQUIRE_API_TOKEN=true:
  - X-API-Token: <HELIX_API_TOKEN>
