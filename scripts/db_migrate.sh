#!/usr/bin/env bash
set -euo pipefail

# Run Alembic migrations using the API container environment.
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "[db_migrate] Running alembic upgrade head ..."
docker compose exec -T api alembic upgrade head

echo "[db_migrate] Done."
