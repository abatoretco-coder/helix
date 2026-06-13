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

"$PROJECT_DIR/scripts/db_restore.sh" "$POSTGRES_BACKUP"

if [ -n "$CONFIG_BACKUP" ]; then
  if [ ! -f "$CONFIG_BACKUP" ]; then
    echo "[restore_all] Config archive not found: $CONFIG_BACKUP"
    exit 1
  fi
  echo "[restore_all] Restoring config archive $CONFIG_BACKUP ..."
  tar -xzf "$CONFIG_BACKUP" -C "$PROJECT_DIR"
fi

echo "[restore_all] Restore completed."
