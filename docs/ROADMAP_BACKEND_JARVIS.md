# Roadmap Backend News -> Helix -> Jarvis

Date: 2026-06-12
Owner: Helix / News backend

## 1) Objectif produit
Construire un backend news personnalise, stable et interfacable, expose via contrat API pour Jarvis Desktop, Jarvis Mobile et autres clients.

## 2) Actions executees (faites)
- [x] Deploiement stack News sur VM300 avec services healthy.
- [x] Resolution conflits de ports (dashboard, freshrss, postgres, redis) via variables d'environnement.
- [x] Aplatissement du repository: contenu de news-nas deplace a la racine de Helix.
- [x] Ajustement documentation et ignore rules apres refactor structure.
- [x] Audit infra VM300 + VM400 + inventaire des stacks docker compose.
- [x] Verification endpoints critiques (dashboard/api/meili/freshrss).

## 3) Roadmap continue (executee autant que possible maintenant)

### Phase A - Stabilisation backend (terminee)
- [x] API FastAPI en production docker
- [x] Workers collect/extract/ai actifs
- [x] Indexation Meilisearch disponible
- [x] Ollama disponible pour embeddings + generation

### Phase B - Contrat API Helix <-> Jarvis (terminee cote specification)
- [x] Contrat formalise dans docs/API_CONTRACT_HELIX_JARVIS.md
- [x] Endpoints existants verifies: /health, /articles, /search, /clusters, /briefings/daily, /jarvis/query
- [x] Versionnage contractuel formel (ex: /v1) implemente
- [x] Auth machine-to-machine (token interne X-API-Token) implemente
- [x] Endpoints profils/feedback implementes pour boucle de personnalisation

### Phase C - Automatisation enrichissement data (partiellement executee)
- [x] Ingestion multi-source active (RSS, HN, GitHub, GNews, Reddit)
- [x] Extraction full-text active avec fallback
- [x] Pipeline AI active (resume, score, embedding)
- [x] Normalisation stricte des sources invalides (ex Reddit libelles mal formes)
- [ ] Scheduler central explicite (cron/celery beat) et SLOs

### Phase D - Industrialisation operationnelle
- [x] Runbook de verification deploiement cree
- [x] Audit de coherence VM/NAS cree
- [x] Monitoring API de base (endpoints pipeline/metrics et sources/status)
- [ ] Alerting centralise (Prometheus/Grafana/Alertmanager)
- [x] Scripts backup/restore PostgreSQL ajoutes
- [ ] Sauvegardes restaurees teste de bout en bout (DB, MinIO, config)

## 4) Priorites recommandees (ordre d'execution)
1. Corriger la normalisation des sources Reddit et les erreurs URL collecteur.
2. Ajouter authentification contractuelle entre Jarvis et API Helix.
3. Ajouter endpoints contractuels de contexte (profiles, feedback, preferences).
4. Ajouter observabilite complete (latence API, lag workers, taux extraction, taux erreurs source).
5. Introduire une strategie de migration schema DB (Alembic) si absente.

## 6) Delta realise dans cette iteration
- [x] API v1 exposee en parallele de l'API legacy
- [x] Auth token configurable sur endpoints /v1
- [x] Endpoints operations: /pipeline/metrics et /sources/status
- [x] Endpoints operations: /pipeline/metrics et /pipeline/sources-status
- [x] Endpoints contractuels: /contract/profiles/upsert, /contract/feedback
- [x] Nouvelles sources validees et ajoutees: Hugging Face Blog, GitHub Changelog, ArXiv cs.CL
- [x] Strategie migration schema en place (Alembic + revision initiale)
- [x] Endpoint Prometheus /metrics expose

## 5) Definition de done backend Jarvis-ready
- API contractuelle stable et versionnee.
- Pipeline data idempotent et observable.
- Zero dependance frontend pour produire valeur metier.
- Jarvis consomme uniquement contrat API et peut restituer sans couplage au dashboard.
