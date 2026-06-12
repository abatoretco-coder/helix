# Gap Analysis - Repos GitHub vs Helix News Backend

Date: 2026-06-12

## 1) Repos de reference a exploiter
- FreshRSS: https://github.com/FreshRSS/FreshRSS
- morss: https://github.com/pictuga/morss
- trafilatura: https://github.com/adbar/trafilatura
- newspaper4k: https://github.com/AussieSeaweed/newspaper4k
- news-please: https://github.com/fhamborg/news-please
- Meilisearch: https://github.com/meilisearch/meilisearch
- Ollama: https://github.com/ollama/ollama
- pgvector: https://github.com/pgvector/pgvector
- FastAPI: https://github.com/fastapi/fastapi

## 2) Couverture actuelle Helix
- Ingestion multi-source: OK
- Extraction multi-strategie: OK
- Stockage + recherche semantique: OK
- API backend pour clients: OK
- Deploiement docker compose local/VM: OK
- Contrat API versionne: PARTIEL
- Auth machine-to-machine: MANQUANT
- Observabilite structuree (metrics/alerts): PARTIEL
- Qualite source (normalisation forte): PARTIEL

## 3) Ecarts fonctionnels principaux
1. Contrat d'API formel versionne et stabilise pour clients Jarvis.
2. Boucle de feedback utilisateur exploitee pour reranking.
3. Monitoring SLO (erreurs collecte, extraction success rate, latency API).
4. Gouvernance schema DB (migrations versionnees automatiques).
5. Hardening securite inter-services (tokens, rotation secrets, least privilege).

## 4) Ecarts techniques detectes dans l'etat runtime
- Conflits de ports hote avec autres stacks (resolus via variables configurables).
- Sources Reddit avec libelles invalides (espaces/tirets) causant erreurs URL.
- Warnings extract worker "raw_item_not_found" a suivre (ordre pipeline / referential integrity).

## 5) Plan de fermeture des gaps
- Semaine 1: API v1 + auth + normalisation sources.
- Semaine 2: metrics + dashboards + alerting.
- Semaine 3: feedback loop et ranking personnalise.
- Semaine 4: tests de charge + runbooks incident + backup/restore tests.
