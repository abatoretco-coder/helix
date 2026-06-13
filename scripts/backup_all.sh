#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
mkdir -p "$BACKUP_DIR"

"$PROJECT_DIR/scripts/db_backup.sh"
"$PROJECT_DIR/scripts/backup_config.sh"
"$PROJECT_DIR/scripts/export_briefings.sh"

echo "[backup_all] All backups completed in $BACKUP_DIR"
