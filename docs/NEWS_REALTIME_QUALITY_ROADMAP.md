# News real-time and quality roadmap

Date: 2026-07-31

## Goal

Increase Helix news coverage, freshness, and trust without creating noisy ingestion or hidden OpenAI cost.

Current baseline after this iteration:

- 295 configured sources.
- 293 enabled sources.
- 82 Google News RSS radars.
- 94 French-language sources.
- 8 ultra-fast 15-minute sources for breaking/cyber/top tech.
- OpenAI usage remains on demand only.

## Operating principles

- Direct RSS feeds are preferred for stable high-quality sources.
- Google News RSS is used as a fast radar layer for discovery and weak spots.
- Priority 1 defaults to 30 minutes; 15 minutes is reserved for breaking news and critical cybersecurity.
- Priority 3 sources default to 120 minutes to protect extraction capacity.
- Source health data should decide which feeds are boosted, slowed, replaced, or disabled.
- No background AI enrichment should be enabled until the recorded usage has been reviewed and a deliberate budget is configured.

## Roadmap

### Phase 1: Static registry quality

- [x] Add `scripts/source_realtime_plan.py` to summarize coverage, cadence, and recommendations.
- [x] Add 20 near-real-time Google News radars, mostly French.
- [x] Slow low-priority radars from 45 minutes to 120 minutes.
- [x] Make collect worker cadence configurable with:
  - `COLLECT_ACTIVE_SLEEP_SECONDS`
  - `COLLECT_IDLE_SLEEP_SECONDS`
  - `COLLECT_MAX_DUE_SOURCES`

### Phase 2: Runtime source triage

- Run `/v1/sources/health` after the NAS stack has collected for 24-72 hours.
- Disable or replace broken feeds with no successful collection.
- Boost high-value feeds with strong conversion and quality.
- Slow noisy feeds with high volume but weak article conversion.
- Replace noisy Google News queries with direct RSS when a recurring source is identified.

### Phase 3: Fresher product response

- [x] Add citation payloads to `/v1/news/summary`.
- [x] Add a freshness SLA in `/v1/news/items`, including a stale warning and target age per view.
- [x] Add a `view=breaking` response restricted to priority-1 sources.
- Add per-scope freshness warnings for Jarvis when selected items are stale.

### Phase 4: More coverage, still controlled

- Raise French-language coverage toward 40% of enabled sources.
- Add more direct French feeds in finance, regulation, cyber, science, and regional industry.
- Add more European institutional feeds for regulation, defense, energy, and supply chain.
- Add focused international feeds for AI infrastructure, chips, cybersecurity, and cloud.

### Phase 5: Cost and reliability guardrails

- [x] Add persisted OpenAI call counters by endpoint, operation, model, and outcome.
- [x] Add daily/monthly and endpoint-specific request caps before any background AI mode is enabled.
- Add extraction queue depth and source lag panels to Grafana.
- Add a weekly source-maintenance report generated from `/v1/sources/recommendations`.

## Validation commands

```powershell
python scripts\source_realtime_plan.py --top 20
python scripts\validate_sources.py --path config\sources.yaml --strict
.\scripts\dev_check.ps1 -StaticOnly
```
