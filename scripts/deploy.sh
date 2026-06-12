#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# News NAS — bootstrap + deploy on NAS (192.168.1.50)
#
# Run once on the NAS:
#   chmod +x scripts/deploy.sh && ./scripts/deploy.sh
#
# Requires: docker, docker compose v2, git, python3
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

NAS_IP="${NAS_IP:-192.168.1.50}"
FRESHRSS_PORT="${FRESHRSS_PORT:-8080}"
DASHBOARD_PORT="${DASHBOARD_PORT:-3000}"
PROMETHEUS_PORT="${PROMETHEUS_PORT:-19090}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "╔══════════════════════════════════════════════════════╗"
echo "║        News NAS — Deploy on ${NAS_IP}              ║"
echo "╚══════════════════════════════════════════════════════╝"
cd "$PROJECT_DIR"

# ── 1. Create .env if missing ─────────────────────────────────────────────────
if [ ! -f .env ]; then
    echo "[1/7] Creating .env from .env.example ..."
    cp .env.example .env
    # Inject NAS IP
    sed -i "s/NAS_IP=.*/NAS_IP=${NAS_IP}/" .env
    echo "      ⚠  Edit .env and set your passwords, then re-run this script."
    echo "      File: $PROJECT_DIR/.env"
    exit 0
fi
echo "[1/7] .env found ✓"

# ── 2. Create data directories ────────────────────────────────────────────────
echo "[2/7] Creating data directories ..."
mkdir -p data/postgres data/minio data/freshrss data/freshrss-ext \
         data/meili data/ollama data/prometheus

# ── 3. Build images ───────────────────────────────────────────────────────────
echo "[3/7] Building Docker images ..."
docker compose build --parallel

# ── 4. Start infrastructure (DB + cache layer) ───────────────────────────────
echo "[4/7] Starting infrastructure services ..."
docker compose up -d postgres redis minio meilisearch freshrss morss

echo "      Waiting for PostgreSQL to be ready ..."
until docker compose exec -T postgres pg_isready -U news -d newsdb -q; do
    sleep 2
done
echo "      PostgreSQL ready ✓"

# ── 5. Start Ollama + pull models ────────────────────────────────────────────
echo "[5/7] Starting Ollama + pulling models ..."
docker compose up -d ollama
sleep 5

echo "      Pulling nomic-embed-text (embeddings) ..."
docker compose exec -T ollama ollama pull nomic-embed-text

echo "      Pulling mistral (summaries / classification) ..."
docker compose exec -T ollama ollama pull mistral

echo "      Models ready ✓"

# ── 6. Import awesome-rss-feeds ───────────────────────────────────────────────
echo "[6/7] Importing feeds from awesome-rss-feeds ..."
if command -v python3 &>/dev/null; then
    python3 scripts/import_awesome_feeds.py \
        --output config/sources.yaml \
        --limit 300 \
        && echo "      Feeds imported ✓" \
        || echo "      ⚠  Feed import failed (non-fatal, continuing)"
else
    echo "      ⚠  python3 not found on host — skipping feed import"
fi

# ── 7. Start all services ────────────────────────────────────────────────────
echo "[7/7] Starting all services ..."
docker compose up -d

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  News NAS is running!                                ║"
echo "║                                                      ║"
echo "║  Dashboard   → http://${NAS_IP}:${DASHBOARD_PORT}              ║"
echo "║  API         → http://${NAS_IP}:8000/docs          ║"
echo "║  FreshRSS    → http://${NAS_IP}:${FRESHRSS_PORT}              ║"
echo "║  Meilisearch → http://${NAS_IP}:7700              ║"
echo "║  MinIO       → http://${NAS_IP}:9001              ║"
echo "║  morss       → http://${NAS_IP}:8081              ║"
echo "║  Prometheus  → http://${NAS_IP}:${PROMETHEUS_PORT}            ║"
echo "║  API Metrics → http://${NAS_IP}:8000/metrics      ║"
echo "║                                                      ║"
echo "║  Logs: docker compose logs -f worker_collect         ║"
echo "╚══════════════════════════════════════════════════════╝"
