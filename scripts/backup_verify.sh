#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="${1:-}"
if [ -z "$TARGET_DIR" ]; then
  echo "Usage: $0 <backup_run_dir>"
  exit 1
fi

if [ ! -d "$TARGET_DIR" ]; then
  echo "[backup_verify][error] backup directory not found: $TARGET_DIR"
  exit 1
fi

manifest_file="$TARGET_DIR/manifest.txt"
postgres_dump="$(find "$TARGET_DIR" -type f -name 'newsdb_*.sql.gz' | head -n1 || true)"
config_archive="$(find "$TARGET_DIR" -type f -name 'config_*.tar.gz' | head -n1 || true)"
exports_dir="$TARGET_DIR/exports"

missing=0

if [ ! -f "$manifest_file" ]; then
  echo "[backup_verify][missing] manifest.txt"
  missing=1
else
  echo "[backup_verify][ok] manifest: $manifest_file"
fi

if [ -z "$postgres_dump" ] || [ ! -f "$postgres_dump" ]; then
  echo "[backup_verify][missing] PostgreSQL dump (newsdb_*.sql.gz)"
  missing=1
else
  echo "[backup_verify][ok] postgres dump: $postgres_dump"
fi

if [ -z "$config_archive" ] || [ ! -f "$config_archive" ]; then
  echo "[backup_verify][missing] config archive (config_*.tar.gz)"
  missing=1
else
  echo "[backup_verify][ok] config archive: $config_archive"
fi

if [ ! -d "$exports_dir" ]; then
  echo "[backup_verify][missing] exports directory: $exports_dir"
  missing=1
else
  echo "[backup_verify][ok] exports directory: $exports_dir"
fi

if [ "$missing" -ne 0 ]; then
  echo "[backup_verify][result] FAILED"
  exit 1
fi

echo "[backup_verify][result] OK"
