# DB Migrations TODO

## Deferred schema changes

- Add `article_ai.anti_dopamine_score` as `numeric(4,3)`.
- Add optional JSON columns for watchlist/research annotations if needed.
- Add `raw_items.next_retry_at` (`timestamp`) for scheduled backoff retries.
- Add table `article_user_state` for read/unread/saved state.
- Add table `watchlist_entities` for persistent watchlist config.
- Add table `entity_mentions` for tracked entity occurrences.
- Add table `research_projects` for DB-backed project definitions.
- Add table `project_articles` for explicit article-to-project links.
- Add table `alert_rules` for notification policies.
- Add table `notification_channels` for outbound delivery config.
- Add table `export_jobs` for async export orchestration.
- Add table `retention_jobs` for cleanup scheduling/auditing.

## Why deferred

- Current release computes anti-dopamine impact in memory during scoring to avoid breaking existing DB schema.
- Migration can be scheduled in a controlled maintenance window.
