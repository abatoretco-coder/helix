#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
RUN_DIR="$BACKUP_DIR/$STAMP"
mkdir -p "$RUN_DIR" "$RUN_DIR/postgres" "$RUN_DIR/config" "$RUN_DIR/exports"

export BACKUP_DIR="$RUN_DIR"
export EXPORT_DIR="$RUN_DIR/exports"

"$PROJECT_DIR/scripts/db_backup.sh"
"$PROJECT_DIR/scripts/backup_config.sh"
"$PROJECT_DIR/scripts/export_briefings.sh"

cat > "$RUN_DIR/manifest.txt" <<EOF
timestamp=$STAMP
postgres_dir=$RUN_DIR
config_dir=$RUN_DIR
exports_dir=$RUN_DIR/exports
EOF

echo "[backup_all] All backups completed in $RUN_DIR"
