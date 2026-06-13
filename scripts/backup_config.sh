#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="$BACKUP_DIR/config_$STAMP.tar.gz"

mkdir -p "$BACKUP_DIR"

echo "[backup_config] Archiving config and docs to $OUT_FILE ..."
tar -czf "$OUT_FILE" \
  .env.example \
  README.md \
  config \
  docs/ROADMAP.md \
  docs/BACKLOG.md \
  docs/ARCHITECTURE_CURRENT.md \
  docs/MVP_CLOSURE_CHECKLIST.md \
  docs/NAS_PRODUCT_ROADMAP.md \
  docs/FEATURE_IDEAS.md \
  docs/DATA_RETENTION_POLICY.md \
  docs/NAS_OPERATIONS.md

echo "[backup_config] Backup complete: $OUT_FILE"
