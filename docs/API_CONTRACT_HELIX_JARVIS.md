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
- GET /v1/search
- GET /v1/briefings/daily
- GET /v1/pipeline/metrics
- GET /v1/sources/status

## 3) Contrat minimal recommande v1

### 3.1 Health
GET /v1/health
- 200: {"status":"ok","service":"news-nas-api"}

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

## 4) Extension contrat recommandee
- POST /v1/profiles/upsert (preferences utilisateur)
- POST /v1/feedback (signal explicite: utile/pas utile)
- GET /v1/sources/status (sante ingestion)
- GET /v1/pipeline/metrics (lag + volumes)

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
