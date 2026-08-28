# Reaudit Repository - 2026-08-16

## Outcome

Helix is now a coherent local-first intelligence service with an explicit boundary around remote AI usage. This pass focused on the gaps between the product roadmap and the runtime contract rather than adding another isolated feature.

## Findings addressed

- News freshness was reported as dates only. `GET /v1/news/items` now publishes item age, a target age, a stale flag, and a safe `view=breaking` mode limited to priority-1 sources.
- News summaries did not expose a stable citation payload. `POST /v1/news/summary` now returns the selected source metadata alongside its text.
- Explicit OpenAI calls were not auditable or budgetable. Calls from summaries, Jarvis answers/embeddings, and semantic search now create a persisted usage event before the request, record tokens/outcome afterwards, and can be capped globally or by endpoint.
- The operational API now exposes `GET /v1/ops/openai-usage` for 1-90 day reporting.
- Compose exposed data-plane services on every host interface while the documentation described a local deployment. PostgreSQL, Redis, MinIO, Meilisearch, morss, and Prometheus now bind to loopback by default. API exposure remains configurable for an on-LAN Jarvis client.
- CORS is no longer wildcard-based. Compose derives approved local/NAS dashboard origins unless `CORS_ALLOW_ORIGINS` is explicitly set.
- The NAS deploy script now applies Alembic migrations after starting the stack and uses the Compose dashboard-port default.

## New configuration

- `OPENAI_DAILY_REQUEST_LIMIT` and `OPENAI_MONTHLY_REQUEST_LIMIT` cap all explicit remote calls.
- `OPENAI_NEWS_SUMMARY_DAILY_REQUEST_LIMIT`, `OPENAI_JARVIS_DAILY_REQUEST_LIMIT`, and `OPENAI_SEMANTIC_SEARCH_DAILY_REQUEST_LIMIT` cap individual flows.
- A value of `0` disables a cap. Keep `BACKGROUND_AI_ENABLED=false`; request caps make endpoint-triggered use visible, not background AI authorised.
- `API_BIND_ADDRESS` controls the API host bind. `PROMETHEUS_BIND_ADDRESS` defaults to loopback.

## Validation completed

- `docker compose config --quiet`
- `python -m ruff check services scripts clients/python/helix_agent_client`
- `python -m compileall services/api/app services/worker/app scripts clients/python/helix_agent_client`
- `python scripts/validate_sources.py --strict`
- `python scripts/source_realtime_plan.py --top 8`
- `npm --prefix dashboard run build`
- `./scripts/dev_check.ps1 -StaticOnly`

## Remaining execution roadmap

1. Run the stack for 24-72 hours, then act on `/v1/sources/health` and `/v1/sources/recommendations`; static source coverage is not proof of feed quality.
2. Add source-lag and extraction-queue panels to Grafana, then set a service-level target from observed data instead of a guessed global threshold.
3. Raise French direct-source coverage toward 40% by replacing proven noisy Google News radars with authoritative RSS feeds.
4. Add integration tests against a disposable PostgreSQL/Redis Compose profile, including one enforced OpenAI cap and the `view=breaking` empty-result path.
5. Keep legacy unversioned endpoints LAN-only; a future public deployment needs server-side dashboard auth and a reverse proxy policy.
