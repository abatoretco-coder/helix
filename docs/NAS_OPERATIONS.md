# Helix NAS Operations

## Backup

- Run the daily PostgreSQL backup job.
- Export configuration files.
- Export generated briefings and Markdown reports.
- Export briefings to Obsidian vault when configured.
- Verify backup archives are readable.
- Use `scripts/backup_all.sh` for a full NAS-friendly backup.
- Use `scripts/backup_config.sh` to archive config and docs.
- Use `scripts/export_briefings.sh` to export briefings as Markdown.
- `backup_all.sh` stores each run under `backups/<timestamp>/` with a `manifest.txt`.
- Use `scripts/backup_verify.sh <backups/<timestamp>>` to validate backup completeness.

## Restore

- Restore PostgreSQL from the latest valid archive.
- Restore configuration from exported files.
- Rebuild search indexes if needed.
- Use `scripts/restore_all.sh <postgres_backup.sql.gz> [config_archive.tar.gz]` for a full restore.
- Set `RESTORE_CONFIRM=true` before restore to avoid accidental destructive restores.
- Set `SKIP_DB_RESTORE=true` to restore only config archives.
- Example:
	- `RESTORE_CONFIRM=true scripts/restore_all.sh backups/newsdb_YYYYMMDD_HHMMSS.sql.gz backups/config_YYYYMMDD_HHMMSS.tar.gz`

## Update

- Pull the latest code.
- Run docker compose config.
- Run scripts/dev_check.sh.
- Rebuild the stack if checks pass.

## Smoke test

- Run scripts/smoke_test.sh after deployment.
- Confirm briefing generation works.
- Confirm runtime services are up.
- Confirm `GET /v1/queues/dead` and `GET /v1/ops/summary` return 200.

## Dev check

- Run scripts/dev_check.sh before pushing changes.
- Use it as the local release gate.

## Dashboard Token Security

- `NEXT_PUBLIC_HELIX_API_TOKEN` is acceptable only for LAN-only NAS usage.
- Do not expose a public dashboard that embeds this token in browser-visible configuration.
- For future external exposure, use server-side auth and/or reverse proxy authentication.

## Logs workers

- worker_collect
- worker_extract
- worker_ai
- worker_cluster
- worker_briefing

## Disk cleanup

- Review MinIO usage.
- Prune stale raw archives according to policy.
- Vacuum PostgreSQL when needed.

## AI usage management

- Keep `BACKGROUND_AI_ENABLED=false` unless background OpenAI costs are explicitly accepted.
- Keep `NEWS_SUMMARY_PROVIDER=local` unless `/v1/news/summary` should call OpenAI.
- Before giving an agent an OpenAI-capable API key, set global and endpoint caps such as `OPENAI_DAILY_REQUEST_LIMIT=50` and `OPENAI_JARVIS_DAILY_REQUEST_LIMIT=20`.
- Review `GET /v1/ops/openai-usage?days=30`; it records only explicit API-triggered remote calls, including failed attempts.
- Use Ollama only as an optional Compose profile on machines with enough resources.

## Network exposure

- PostgreSQL, Redis, MinIO, Meilisearch, morss, and Prometheus are bound to `127.0.0.1` in Compose.
- Keep the API on the LAN only unless an authenticated reverse proxy is in front of it. Set `API_BIND_ADDRESS=127.0.0.1` when no remote Jarvis client is needed.
- Leave `CORS_ALLOW_ORIGINS` empty to derive the local and `NAS_IP` dashboard origins, or set it to exact approved origins. Wildcard CORS is intentionally not used.

## Troubleshooting

- Check docker compose ps.
- Inspect worker logs.
- Verify Redis queues.
- Inspect dead-letter queues with `/v1/queues/dead` and retry/purge via API when needed.
- Confirm Postgres and MinIO health.

## Obsidian export

- Configure `OBSIDIAN_EXPORT_ENABLED=true` in `.env` to enable export.
- Optional path override: `OBSIDIAN_EXPORT_PATH=exports/obsidian`.
- Run `scripts/export_briefings.sh` to export markdown plus Obsidian-friendly files.
