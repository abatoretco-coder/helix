#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "[dev-check] validating docker compose config"
docker compose config >/dev/null

echo "[dev-check] compiling worker python files"
python -m compileall services/worker/app

echo "[dev-check] compiling api python files"
python -m compileall services/api/app

echo "[dev-check] validating source registry"
python scripts/validate_sources.py --strict

echo "[dev-check] checking running containers"
running_services="$(docker compose ps --services --filter status=running)"
if [ -z "$running_services" ] || ! echo "$running_services" | grep -qx "api"; then
  echo "Run docker compose up -d --build first."
  exit 1
fi

echo "[dev-check] running smoke test"
bash scripts/smoke_test.sh

echo "[dev-check] all checks passed"
