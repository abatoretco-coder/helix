#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <backup_file.sql.gz>"
  exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

BACKUP_FILE="$1"
if [ ! -f "$BACKUP_FILE" ]; then
  echo "[db_restore] File not found: $BACKUP_FILE"
  exit 1
fi

echo "[db_restore] Restoring $BACKUP_FILE into newsdb ..."
gzip -dc "$BACKUP_FILE" | docker compose exec -T postgres psql -U news -d newsdb

echo "[db_restore] Restore completed."
