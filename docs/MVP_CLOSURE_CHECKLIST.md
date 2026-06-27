# Helix MVP Closure Checklist

## Runtime and stack

- [ ] docker compose config passes
- [ ] All runtime services start and stay healthy
- [ ] worker_extract depends on postgres, redis, minio, morss
- [ ] worker_ai depends on ollama
- [ ] worker_cluster service is enabled
- [ ] worker_briefing service is enabled
- [ ] worker_cleanup service is enabled
- [ ] daily scheduler is embedded in worker_briefing

## Pipeline behavior

- [ ] collect enqueues queue:extract
- [ ] extract enqueues queue:ai
- [ ] ai enqueues queue:cluster after DB commit
- [ ] cluster writes clusters and article_clusters
- [ ] briefing consumes queue:briefing and upserts daily briefings
- [ ] cleanup periodically deletes old processing logs and stale failed/duplicate raw items
- [ ] briefing payload parser falls back to current date when date is missing/invalid
- [ ] cluster worker explicitly checks ai.embedding is None

## Verification

- [ ] scripts/smoke_test.sh passes
- [ ] scripts/dev_check.sh passes
- [ ] scripts/dev_check.ps1 -StaticOnly passes on Windows development hosts
- [ ] GET /health and GET /v1/health return 200
- [ ] GET /sources returns 200
- [ ] GET /articles returns 200
- [ ] GET /search returns 200
- [ ] GET /clusters returns 200 or 307 -> /clusters/
- [ ] GET /v1/queues/dead returns 200
- [ ] GET /v1/ops/summary returns 200
- [ ] POST /briefings/generate returns 202
- [ ] GET /briefings/daily is accepted as 200 or 404 on fresh install

## Ops and docs

- [ ] .env.example includes scheduler/retry/obsidian variables
- [ ] README lists five workers and embedded scheduler note
- [ ] docs/ROADMAP.md exists
- [ ] docs/BACKLOG.md exists
- [ ] docs/ARCHITECTURE_CURRENT.md exists
- [ ] docs/MVP_CLOSURE_CHECKLIST.md exists
