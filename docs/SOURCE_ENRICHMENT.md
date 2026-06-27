# Source Enrichment

Helix keeps the canonical source registry in `config/sources.yaml`. The
`worker_collect` service syncs enabled YAML sources into PostgreSQL before each
collection cycle, so adding sources to the registry is enough to seed the
database on the next worker run.

## Current registry

After the curated enrichment pass, the registry contains:

- 275 total sources.
- 79 French-language sources.
- 62 Google News RSS topic radars.
- 197 direct RSS/Atom feeds.
- 8 Reddit feeds, 4 GitHub Trending feeds, 2 Hacker News feeds, and 2 YouTube feeds.

The French-first expansion adds national news, tech, AI, cybersecurity,
regulation, economy, science, energy, health, logistics, defense, and
geopolitics coverage. International additions cover AI labs, cybersecurity,
science, infrastructure, and high-signal topic monitoring.

## Curated pack

Run the idempotent curated importer:

```bash
python scripts/enrich_sources.py --dry-run
python scripts/enrich_sources.py
python scripts/validate_sources.py --strict
```

The script deduplicates with the same identity rules as
`scripts/validate_sources.py`:

- RSS and sitemap: `type + url`.
- Google News RSS: `query + language + country`.
- Reddit: `subreddit`.
- Hacker News: `hn_type`.
- GitHub Trending: `topic + language_filter`.
- YouTube channel: `channel_id`.

It appends only missing entries, preserving the existing YAML as much as
possible. Re-running it should print `Nothing new to add` once the pack is
fully applied.

## Broad OPML import

For a larger but less curated import, use the OPML importer:

```bash
python scripts/import_awesome_feeds.py --output config/sources.yaml --limit 500
python scripts/validate_sources.py --strict
```

Use the curated pack first, then OPML import for breadth.

## Applying to the database

Restart or let the collector cycle run:

```bash
docker compose restart worker_collect
```

The collector inserts YAML sources that are not already present in the
`sources` table. Existing database rows keep their runtime state, such as
error counts and dashboard-enabled flags.

## Monitoring quality

The dashboard Sources page uses `GET /v1/sources/health?limit=500` to show the
full registry with operational quality signals:

- 24h and 7d raw item counts.
- 24h and 7d extraction/article counts.
- Raw-item error counts.
- Raw-to-article conversion rate.
- Extraction success rate.
- Average article quality score.
- Dominant extracted article language and mismatch rate.
- Health score from 0 to 100.
- Quality band: `healthy`, `high_value`, `watch`, `noisy`, `stale`,
  `broken`, or `disabled`.
- Recommendation: suggested action, severity, rationale, and optional target
  priority.

Use this cockpit after any large source import. High-volume sources with low
conversion or quality should be disabled, lowered in priority, or replaced by
more precise feeds.

For an operations queue, call:

```bash
curl http://localhost:8000/v1/sources/recommendations?limit=50
```

Recommendations include:

- `disable`: retire broken or very low-health sources.
- `refresh_or_disable`: force a refresh before retiring stale feeds.
- `lower_priority`: slow noisy/high-volume low-quality sources.
- `boost_priority`: collect high-value sources more often.
- `review_language`: correct source metadata when detected article languages
  disagree with the configured language.
- `monitor_errors`: reset or watch sources with recent raw item errors.

## Recommended follow-ups

- Add a source-management UI for OPML import/export and curated pack previews.
- Add automatic stale-source detection for feeds that repeatedly return zero
  items or extraction failures.
