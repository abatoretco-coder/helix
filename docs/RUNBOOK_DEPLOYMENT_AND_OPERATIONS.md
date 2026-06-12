# Runbook - Deployment and Operations

## 1) Deploiement VM300

### 1.1 Sync code
ssh vm300 "cd /opt/naas/stacks/news-nas; git fetch origin; git reset --hard origin/main"

### 1.2 Variables essentielles (.env)
- NAS_IP=192.168.1.175
- DASHBOARD_PORT=13000
- FRESHRSS_PORT=8082
- POSTGRES_PORT=55432
- REDIS_PORT=56379

### 1.3 Start
ssh vm300 "cd /opt/naas/stacks/news-nas; docker compose up -d"

### 1.4 Verification
ssh vm300 "cd /opt/naas/stacks/news-nas; docker compose ps"

## 2) Verification endpoints
- Dashboard: http://192.168.1.175:13000
- API health: http://192.168.1.175:8000/health
- Meilisearch: http://192.168.1.175:7700/health
- FreshRSS: http://192.168.1.175:8082
- Prometheus metrics: http://192.168.1.175:8000/metrics
- Pipeline metrics: http://192.168.1.175:8000/v1/pipeline/metrics
- Source status: http://192.168.1.175:8000/v1/pipeline/sources-status

## 3) Logs utiles
ssh vm300 "cd /opt/naas/stacks/news-nas; docker compose logs --tail 100 api"
ssh vm300 "cd /opt/naas/stacks/news-nas; docker compose logs --tail 100 worker_collect"
ssh vm300 "cd /opt/naas/stacks/news-nas; docker compose logs --tail 100 worker_extract"
ssh vm300 "cd /opt/naas/stacks/news-nas; docker compose logs --tail 100 worker_ai"

## 4) Incidents courants
- Port deja alloue: changer variables *_PORT dans .env et relancer.
- API unhealthy: verifier dependances postgres/redis/meili puis logs api.
- Collect errors source: verifier format de sources.yaml.
- Slow AI: verifier modeles Ollama et ressources CPU/RAM.

## 5) Procedure de rollback simple
- Revenir au commit precedent:
  ssh vm300 "cd /opt/naas/stacks/news-nas; git log --oneline -n 5"
  ssh vm300 "cd /opt/naas/stacks/news-nas; git reset --hard <commit>; docker compose up -d"

## 6) Migrations base de donnees (Alembic)
ssh vm300 "cd /opt/naas/stacks/news-nas; docker compose exec -T api alembic upgrade head"

## 7) Backup / restore PostgreSQL
ssh vm300 "cd /opt/naas/stacks/news-nas; ./scripts/db_backup.sh"
ssh vm300 "cd /opt/naas/stacks/news-nas; ./scripts/db_restore.sh backups/newsdb_YYYYMMDD_HHMMSS.sql.gz"
