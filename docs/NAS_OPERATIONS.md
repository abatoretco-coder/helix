# Helix NAS Operations

## Backup

- Run the daily PostgreSQL backup job.
- Export configuration files.
- Export generated briefings and Markdown reports.
- Verify backup archives are readable.
- Use `scripts/backup_all.sh` for a full NAS-friendly backup.
- Use `scripts/backup_config.sh` to archive config and docs.
- Use `scripts/export_briefings.sh` to export briefings as Markdown.

## Restore

- Restore PostgreSQL from the latest valid archive.
- Restore configuration from exported files.
- Rebuild search indexes if needed.
- Use `scripts/restore_all.sh <postgres_backup.sql.gz> [config_archive.tar.gz]` for a full restore.

## Update

- Pull the latest code.
- Run docker compose config.
- Run scripts/dev_check.sh.
- Rebuild the stack if checks pass.

## Smoke test

- Run scripts/smoke_test.sh after deployment.
- Confirm briefing generation works.
- Confirm runtime services are up.

## Dev check

- Run scripts/dev_check.sh before pushing changes.
- Use it as the local release gate.

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

## Ollama model management

- Verify installed models.
- Pull missing embedding and summary models.
- Keep parallelism low on constrained NAS hardware.

## Troubleshooting

- Check docker compose ps.
- Inspect worker logs.
- Verify Redis queues.
- Confirm Postgres and MinIO health.
