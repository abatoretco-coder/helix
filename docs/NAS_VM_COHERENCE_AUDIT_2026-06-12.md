# Audit de Coherence VM/NAS

Date: 2026-06-12
Perimetre auditable: vm300 (192.168.1.175), vm400 (192.168.1.38)

## 1) VM300 (app-host)
- Docker: 26.1.5
- Compose: 2.26.1
- Stack Helix/News: en execution
- Services News actifs: api, dashboard, postgres, redis, meilisearch, minio, freshrss, morss, ollama, workers

### Ports Helix sur VM300 (etat actuel)
- Dashboard: 13000 -> 3000
- API: 8000 -> 8000
- Meilisearch: 7700 -> 7700
- FreshRSS: 8082 -> 80
- Postgres: 55432 -> 5432
- Redis: 56379 -> 6379
- MinIO: 9000/9001
- Ollama: 11434

### Cohabitation avec autres stacks detectees
- kargo-preprod (utilise 3000, 5432, etc.)
- nextcloud (utilise 8080)
- plex, syncthing

Conclusion VM300:
- Cohabitation OK apres parametrage des ports Helix.
- Risque principal residuel: collisions futures de ports si nouvelles stacks.

## 2) VM400 (home-assistant)
- Docker: 26.1.5
- Compose: 2.26.1
- Stacks detectees: home-assistant, Jarvis, Mijot
- Helix/News non deploye sur vm400.

## 3) Coherence globale infra
- Separation des roles observee:
  - vm300: workloads applicatifs NAS/news + apps annexes
  - vm400: home assistant + Jarvis ecosystem
- Contrat Helix->Jarvis pertinent car Jarvis tourne deja sur vm400.

## 4) Recommandations coherence
1. Formaliser un registre central des ports par VM.
2. Ajouter une convention de nommage des stacks compose.
3. Definir un chemin standard de deploiement pour Helix: /opt/naas/stacks/news-nas.
4. Ajouter health probes cross-VM (Jarvis vers API Helix).
