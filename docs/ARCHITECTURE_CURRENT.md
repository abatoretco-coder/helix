# Helix Current Architecture

## Runtime services

- postgres
- redis
- minio
- morss
- freshrss
- meilisearch
- ollama
- api
- worker_collect
- worker_extract
- worker_ai
- worker_cluster
- worker_briefing
- dashboard
- prometheus

## Data flow

sources.yaml / DB sources
→ worker_collect
→ raw_items
→ queue:extract
→ worker_extract
→ articles + MinIO
→ queue:ai
→ worker_ai
→ article_ai + Meilisearch
→ queue:cluster
→ worker_cluster
→ clusters + article_clusters
→ queue:briefing
→ worker_briefing
→ briefings (and embedded daily scheduler trigger)
→ API / Dashboard / Jarvis

## Queues

- queue:extract
- queue:ai
- queue:cluster
- queue:briefing

## Main tables

- sources
- raw_items
- articles
- article_ai
- clusters
- article_clusters
- briefings
- processing_logs

## Main endpoints

- GET /health
- GET /v1/health
- GET /sources
- GET /articles
- GET /search
- GET /clusters
- GET /briefings/daily
- POST /briefings/generate
- POST /jarvis/query
- GET /metrics
