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
- worker_cleanup
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
→ worker_cleanup
→ retention_jobs + old-log/raw-item cleanup
→ API / Dashboard / Jarvis

## Queues

- queue:extract
- queue:ai
- queue:cluster
- queue:briefing
- queue:extract:dead
- queue:ai:dead
- queue:cluster:dead
- queue:briefing:dead

## Main tables

- sources
- raw_items
- articles
- article_ai
- clusters
- article_clusters
- briefings
- processing_logs
- article_user_state
- watchlist_entities
- entity_mentions
- research_projects
- project_articles
- notification_channels
- alert_rules
- export_jobs
- retention_jobs

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
- GET /ops/summary
- GET /queues/dead
- GET /watchlist
- GET /projects
- GET /inbox
