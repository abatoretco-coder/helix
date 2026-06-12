#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="$BACKUP_DIR/newsdb_$STAMP.sql.gz"

echo "[db_backup] Creating backup at $OUT_FILE ..."
docker compose exec -T postgres pg_dump -U news -d newsdb | gzip > "$OUT_FILE"

echo "[db_backup] Backup complete: $OUT_FILE"
