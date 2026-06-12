# Helix MVP Closure Checklist

## Runtime and stack

- [ ] docker compose config passes
- [ ] All runtime services start and stay healthy
- [ ] worker_extract depends on postgres, redis, minio, morss
- [ ] worker_ai depends on ollama
- [ ] worker_cluster service is enabled
- [ ] worker_briefing service is enabled
- [ ] worker_scheduler service is enabled

## Pipeline behavior

- [ ] collect enqueues queue:extract
- [ ] extract enqueues queue:ai
- [ ] ai enqueues queue:cluster after DB commit
- [ ] cluster writes clusters and article_clusters
- [ ] briefing consumes queue:briefing and upserts daily briefings
- [ ] briefing payload parser falls back to current date when date is missing/invalid
- [ ] cluster worker explicitly checks ai.embedding is None

## Verification

- [ ] scripts/smoke_test.sh passes
- [ ] scripts/dev_check.sh passes
- [ ] GET /health and GET /v1/health return 200
- [ ] GET /sources returns 200
- [ ] GET /articles returns 200
- [ ] GET /search returns 200
- [ ] GET /clusters returns 200 or 307 -> /clusters/
- [ ] POST /briefings/generate returns 202
- [ ] GET /briefings/daily is accepted as 200 or 404 on fresh install

## Ops and docs

- [ ] .env.example includes scheduler variables
- [ ] README lists six workers
- [ ] docs/ROADMAP.md exists
- [ ] docs/BACKLOG.md exists
- [ ] docs/ARCHITECTURE_CURRENT.md exists
- [ ] docs/MVP_CLOSURE_CHECKLIST.md exists
