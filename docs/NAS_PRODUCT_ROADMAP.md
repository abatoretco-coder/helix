# Helix NAS Product Roadmap

## Phase 1 — NAS cockpit

- [x] Pipeline health page
- [x] Source health page
- [x] Queue monitoring
- [x] Error dashboard
- [x] Manual dead-letter retry/purge actions

## Phase 2 — Storage and retention

- MinIO structured raw archive
- Retention policy
- Cleanup worker
- [x] Backup all script
- [x] Restore all script
- [x] Export briefings to Markdown and Obsidian layout

## Phase 3 — Personal intelligence

- [x] User profile config
- [x] Personal relevance scoring
- [x] Anti-dopamine score (without destructive migration)
- [x] Watchlist entities + matches endpoint
- Trend detection
- Similar articles
- Cluster timeline

## Phase 4 — Jarvis integration

- [x] Stable /v1/jarvis/query (v2 contract with backward compatibility)
- Source-cited answers
- Voice briefing mode
- Topic-specific briefings
- Alert endpoint

## Phase 5 — NAS ecosystem

- [x] Home Assistant webhook skeleton
- [x] Obsidian Markdown export
- Paperless-ngx export
- Plex cultural recommendations
- Notification channels

## Phase 6 — Reliability

- [x] Dead-letter queues
- [x] Retry policies
- [x] Worker rate limits (global + per worker)
- [x] Low power mode
- [x] Backup verification
- Grafana dashboard
