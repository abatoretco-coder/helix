#!/usr/bin/env bash
set -euo pipefail

# Import Helix dashboard into an existing Grafana instance.
# Required:
#   GRAFANA_URL (e.g. http://192.168.1.175:3000)
#   GRAFANA_TOKEN (Grafana service account token)
# Optional:
#   GRAFANA_FOLDER_ID (default: 0)
#   GRAFANA_OVERWRITE (default: true)

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DASH_FILE="$PROJECT_DIR/monitoring/grafana/helix-news-overview.json"

if [ -z "${GRAFANA_URL:-}" ] || [ -z "${GRAFANA_TOKEN:-}" ]; then
  echo "Usage: GRAFANA_URL=... GRAFANA_TOKEN=... $0"
  exit 1
fi

if [ ! -f "$DASH_FILE" ]; then
  echo "Dashboard file not found: $DASH_FILE"
  exit 1
fi

FOLDER_ID="${GRAFANA_FOLDER_ID:-0}"
OVERWRITE="${GRAFANA_OVERWRITE:-true}"

PAYLOAD_FILE="$(mktemp)"
trap 'rm -f "$PAYLOAD_FILE"' EXIT

{
  echo '{"dashboard":'
  cat "$DASH_FILE"
  echo ',"folderId":'"$FOLDER_ID"',"overwrite":'"$OVERWRITE"'}'
} > "$PAYLOAD_FILE"

curl -fsS -X POST "${GRAFANA_URL%/}/api/dashboards/db" \
  -H "Authorization: Bearer ${GRAFANA_TOKEN}" \
  -H "Content-Type: application/json" \
  --data-binary @"$PAYLOAD_FILE"

echo
echo "[grafana] Dashboard import request sent successfully."
