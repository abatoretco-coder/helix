#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
STAMP_ISO="$(date -Iseconds)"
RUN_DIR="$BACKUP_DIR/$STAMP"
mkdir -p "$RUN_DIR" "$RUN_DIR/postgres" "$RUN_DIR/config" "$RUN_DIR/exports"

export BACKUP_DIR="$RUN_DIR"
export EXPORT_DIR="$RUN_DIR/exports"

"$PROJECT_DIR/scripts/db_backup.sh"
"$PROJECT_DIR/scripts/backup_config.sh"
"$PROJECT_DIR/scripts/export_briefings.sh"

DB_DUMP_FILE="$(find "$RUN_DIR" -maxdepth 1 -type f -name 'newsdb_*.sql.gz' | head -n1 || true)"
CONFIG_ARCHIVE_FILE="$(find "$RUN_DIR" -maxdepth 1 -type f -name 'config_*.tar.gz' | head -n1 || true)"

db_size=0
config_size=0
if [ -n "$DB_DUMP_FILE" ] && [ -f "$DB_DUMP_FILE" ]; then
	db_size="$(wc -c < "$DB_DUMP_FILE")"
fi
if [ -n "$CONFIG_ARCHIVE_FILE" ] && [ -f "$CONFIG_ARCHIVE_FILE" ]; then
	config_size="$(wc -c < "$CONFIG_ARCHIVE_FILE")"
fi

git_commit="unknown"
if git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
	git_commit="$(git -C "$PROJECT_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
fi

cat > "$RUN_DIR/manifest.txt" <<EOF
timestamp=$STAMP
timestamp_iso=$STAMP_ISO
git_commit=$git_commit
postgres_dir=$RUN_DIR
config_dir=$RUN_DIR
exports_dir=$RUN_DIR/exports
db_dump_file=${DB_DUMP_FILE:-}
db_dump_size_bytes=$db_size
config_archive_file=${CONFIG_ARCHIVE_FILE:-}
config_archive_size_bytes=$config_size
EOF

bash "$PROJECT_DIR/scripts/backup_verify.sh" "$RUN_DIR"

echo "[backup_all] All backups completed in $RUN_DIR"
