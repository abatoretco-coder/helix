#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

if [ -f .env ]; then
  # shellcheck disable=SC1091
  source .env
fi

API_BASE="${API_BASE:-http://127.0.0.1:8000}"

AUTH_HEADER=()
if [ "${REQUIRE_API_TOKEN:-false}" = "true" ] && [ -n "${HELIX_API_TOKEN:-}" ]; then
  AUTH_HEADER=(-H "X-API-Token: ${HELIX_API_TOKEN}")
fi

run_http() {
  local method="$1"
  local url="$2"

  if command -v curl >/dev/null 2>&1; then
    if [ "$method" = "GET" ]; then
      curl -fsS "${AUTH_HEADER[@]}" "$url" >/dev/null
    else
      curl -fsS -X "$method" "${AUTH_HEADER[@]}" "$url" >/dev/null
    fi
    return
  fi

  # Fallback for minimal NAS hosts without curl installed.
  if [ "$method" = "GET" ]; then
    docker compose exec -T api curl -fsS "${AUTH_HEADER[@]}" "$url" >/dev/null
  else
    docker compose exec -T api curl -fsS -X "$method" "${AUTH_HEADER[@]}" "$url" >/dev/null
  fi
}

check_get() {
  local path="$1"
  echo "[smoke] GET ${path}"
  run_http "GET" "${API_BASE}${path}"
}

check_post() {
  local path="$1"
  echo "[smoke] POST ${path}"
  run_http "POST" "${API_BASE}${path}"
}

echo "[smoke] API base: ${API_BASE}"
check_get "/health"
check_get "/v1/health"
check_get "/sources"
check_get "/articles?limit=1"
check_get "/search?q=test"
check_get "/clusters"
check_post "/briefings/generate?period=daily&category=all"

echo "[smoke] checking container runtime"
required_services=(
  postgres
  redis
  minio
  meilisearch
  api
  worker_collect
  worker_extract
  worker_ai
  worker_cluster
  worker_briefing
)

running_services="$(docker compose ps --services --filter status=running)"

for service in "${required_services[@]}"; do
  if ! echo "$running_services" | grep -qx "$service"; then
    echo "[smoke][error] service not running: $service"
    exit 1
  fi
  echo "[smoke] service running: $service"
done

echo "[smoke] all checks passed"
