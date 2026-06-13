# DB Migrations TODO

## Deferred schema changes

- Add `article_ai.anti_dopamine_score` as `numeric(4,3)`.
- Add optional JSON columns for watchlist/research annotations if needed.
- Add `raw_items.next_retry_at` (`timestamp`) for scheduled backoff retries.

## Why deferred

- Current release computes anti-dopamine impact in memory during scoring to avoid breaking existing DB schema.
- Migration can be scheduled in a controlled maintenance window.
