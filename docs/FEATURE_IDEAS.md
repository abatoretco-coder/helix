# Helix Feature Ideas

## Intelligent Inbox

Objective: surface the right articles first and hide low-value noise.

Value: turns the feed firehose into a daily action list.

Potential tables: articles, article_ai, clusters, processing_logs, read_state, favorites.

Potential endpoints: GET /v1/inbox, POST /v1/articles/{id}/read, POST /v1/articles/{id}/save.

Priority: P0.

## Source Health

Objective: show per-source reliability, freshness, and extraction quality.

Value: prevents the registry from becoming unmaintainable.

Potential tables: sources, raw_items, processing_logs, source_stats.

Potential endpoints: GET /v1/sources/health, POST /v1/sources/{id}/disable, POST /v1/sources/{id}/refresh.

Priority: P0.

## Research Projects

Objective: group articles around an ongoing topic or investigation.

Value: creates a personal research workspace over the news history.

Potential tables: projects, project_articles, project_notes.

Potential endpoints: POST /v1/projects, GET /v1/projects/{id}, POST /v1/projects/{id}/articles.

Priority: P1.

## Watchlist

Objective: track entities, keywords, and topics over time.

Value: produces alerts and weekly summaries for items that matter.

Potential tables: watchlist_entities, entity_mentions, entity_daily_stats.

Potential endpoints: GET /v1/watchlist, POST /v1/watchlist, GET /v1/watchlist/{id}/stats.

Priority: P1.

## Daily French Briefing

Objective: generate a concise morning briefing in French.

Value: makes Helix usable as a daily executive summary.

Potential tables: briefings, briefing_preferences, user_profile.

Potential endpoints: GET /v1/briefings/daily?style=executive&language=fr, POST /v1/briefings/generate.

Priority: P0.

## Anti-Dopamine Filter

Objective: downrank clickbait, outrage, repetition, and low-density content.

Value: reduces feed fatigue and improves signal quality.

Potential tables: article_ai, source_stats, filter_rules, filtered_articles.

Potential endpoints: GET /v1/articles/filtered, POST /v1/articles/{id}/override.

Priority: P1.

## Timeline per Cluster

Objective: present the evolution of an event over time.

Value: helps follow complex stories and understand context.

Potential tables: clusters, article_clusters, cluster_events.

Potential endpoints: GET /v1/clusters/{cluster_id}/timeline.

Priority: P1.

## Obsidian Export

Objective: export briefings and research notes as Markdown vault files.

Value: preserves a portable long-term memory outside the database.

Potential tables: briefings, exports, export_jobs.

Potential endpoints: POST /v1/exports/obsidian, GET /v1/exports.

Priority: P2.

## Home Assistant Notifications

Objective: notify the home automation stack when important events happen.

Value: brings Helix into the NAS ecosystem and mobile alert flow.

Potential tables: notifications, notification_channels, alert_rules.

Potential endpoints: POST /v1/home-assistant/briefing-ready, POST /v1/home-assistant/alert.

Priority: P2.

## Jarvis Voice Briefing

Objective: expose a source-cited briefing format suitable for voice assistants.

Value: gives Jarvis a stable and actionable news response format.

Potential tables: briefings, jarvis_requests, jarvis_responses.

Potential endpoints: POST /v1/jarvis/query, POST /v1/jarvis/voice-briefing.

Priority: P1.

## NAS Low Power Mode

Objective: reduce CPU and IO pressure during off hours.

Value: keeps Helix sustainable on a home NAS.

Potential tables: scheduler_jobs, worker_limits, maintenance_windows.

Potential endpoints: GET /v1/system/power-mode, POST /v1/system/power-mode.

Priority: P2.

## Dead Letter Queues

Objective: isolate permanently failing jobs from the main queues.

Value: prevents infinite retry loops and improves operability.

Potential tables: processing_logs, dead_letter_items, retry_state.

Potential endpoints: GET /v1/queues/dead, POST /v1/queues/dead/{id}/retry.

Priority: P0.

## Backup and Restore

Objective: make the whole stack recoverable on NAS hardware.

Value: lowers operational risk and makes upgrades safer.

Potential tables: backup_jobs, restore_jobs, export_jobs.

Potential endpoints: POST /v1/backups/run, POST /v1/restores/run, GET /v1/backups.

Priority: P0.

## Grafana Observability

Objective: expose throughput, errors, queue depth, and storage usage.

Value: makes failures visible before users notice them.

Potential tables: metrics_snapshots, worker_stats, source_stats.

Potential endpoints: GET /v1/pipeline/status, GET /v1/pipeline/queues, GET /v1/pipeline/errors.

Priority: P0.
