#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <postgres_backup.sql.gz> [config_archive.tar.gz]"
  exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

POSTGRES_BACKUP="$1"
CONFIG_BACKUP="${2:-}"
SKIP_DB_RESTORE="${SKIP_DB_RESTORE:-false}"
RESTORE_CONFIRM="${RESTORE_CONFIRM:-false}"

if [ "$RESTORE_CONFIRM" != "true" ]; then
  echo "[restore_all] Refusing to run without RESTORE_CONFIRM=true"
  echo "[restore_all] Example: RESTORE_CONFIRM=true $0 backups/newsdb_YYYYMMDD_HHMMSS.sql.gz backups/config_YYYYMMDD_HHMMSS.tar.gz"
  exit 1
fi

echo "[restore_all][warning] This operation may overwrite live data."

if [ "$SKIP_DB_RESTORE" != "true" ]; then
  if [ ! -f "$POSTGRES_BACKUP" ]; then
    echo "[restore_all] PostgreSQL backup not found: $POSTGRES_BACKUP"
    exit 1
  fi
  "$PROJECT_DIR/scripts/db_restore.sh" "$POSTGRES_BACKUP"
else
  echo "[restore_all] SKIP_DB_RESTORE=true -> skipping database restore"
fi

if [ -n "$CONFIG_BACKUP" ]; then
  if [ ! -f "$CONFIG_BACKUP" ]; then
    echo "[restore_all] Config archive not found: $CONFIG_BACKUP"
    exit 1
  fi
  echo "[restore_all] Restoring config archive $CONFIG_BACKUP ..."
  tar -xzf "$CONFIG_BACKUP" -C "$PROJECT_DIR"
fi

echo "[restore_all] Restore completed."
