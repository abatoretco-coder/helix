#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
EXPORT_DIR="${EXPORT_DIR:-$BACKUP_DIR/exports}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="$EXPORT_DIR/briefings_$STAMP"

mkdir -p "$OUT_DIR"

echo "[export_briefings] Exporting briefings to $OUT_DIR ..."
docker compose exec -T postgres psql -U news -d newsdb -c "copy (select id, period, period_date, category, content, generated_at from briefings order by period_date desc, id desc) to stdout with csv header" \
  | python3 - "$OUT_DIR" <<'PY'
import csv
import pathlib
import sys

out_dir = pathlib.Path(sys.argv[1])
reader = csv.DictReader(sys.stdin)
count = 0
for row in reader:
    period = row.get("period") or "daily"
    period_date = (row.get("period_date") or "").split(" ")[0]
    category = row.get("category") or "all"
    generated_at = row.get("generated_at") or ""
    briefing_id = row.get("id") or str(count + 1)
    filename = f"{period_date}_{category}_{briefing_id}.md".replace(":", "-")
    content = row.get("content") or ""
    markdown = f"---\nid: {briefing_id}\nperiod: {period}\ndate: {period_date}\ncategory: {category}\ngenerated_at: {generated_at}\n---\n\n{content}"
    (out_dir / filename).write_text(markdown, encoding="utf-8")
    count += 1
print(f"[export_briefings] Exported {count} briefing files")
PY

echo "[export_briefings] Export complete: $OUT_DIR"

echo "[export_briefings] Exporting to Obsidian vault if configured"
python3 "$PROJECT_DIR/scripts/export_briefings_obsidian.py"
