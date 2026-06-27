# DB Migrations TODO

## Deferred schema changes

- Add `article_ai.anti_dopamine_score` as `numeric(4,3)`.
- Add optional JSON columns for watchlist/research annotations if needed.
- Add a controlled migration path for large historical tables before tightening nullable columns.

## Why deferred

- Current release computes anti-dopamine impact in memory during scoring to avoid breaking existing DB schema.
- Productization and retry-backoff tables/columns now exist in Alembic and fresh-install SQL.
- Raw HTML/JSON object retention is handled by `worker_cleanup`; remaining DB changes need a controlled maintenance window.
