# Sélection de sources et workflow IA Helix

## Situation de départ — 24 août 2026

- 293 sources actives.
- 5 056 articles actifs, dont 4 712 publiés depuis moins de sept jours.
- 5 357 articles ont été collectés par les sources de priorité 2 sur les dernières 24 heures.
- Les catégories `countries` et `recommended` fournissent environ 4 308 articles sur sept jours, majoritairement hors périmètre.
- Ollama traite une fiche en 8 à 27 secondes. Le coût est local, mais la capacité de calcul est limitée ; elle doit servir aux contenus pertinents.

## Politique cible

1. Garder les catégories dédiées : `ai`, `supply_chain`, `pharma`, `climate`, `cybersecurity`, `startups`.
2. Garder sous condition de mots-clés : `tech`, `science`, `regulation`, `geopolitics`, `finance`.
3. Suspendre du workflow actif : `countries`, `recommended`, `general`, `travel`.
4. Ne jamais envoyer à Ollama un candidat de plus de sept jours ; l’archivage réversible prend le relais à trente jours.

La politique est versionnée dans `config/source_policy.yaml`. Elle ne supprime ni le catalogue de sources ni les données historiques : modifier le YAML puis redémarrer les workers suffit pour ajuster le périmètre.

## Mesures déjà implantées

- Admission avant la collecte : une source suspendue n’est plus interrogée.
- Admission avant l’extraction : les éléments déjà présents mais hors politique sont marqués `filtered_out`.
- Admission avant Ollama : un article hors politique, trop ancien ou archivé ne consomme pas de génération.
- Une seule génération JSON par article ; en cas d’échec, des valeurs déterministes remplacent les appels LLM de secours.
- Plafond de sortie à 320 tokens par article.
- Embeddings locaux `nomic-embed-text` (768 dimensions) pour réactiver le clustering et la recherche sémantique sans OpenAI.
- Rapport non destructif : `python -m app.tools.source_viability` dans `news_worker_ai`.

## Phases suivantes

### Phase 1 — Stabiliser et observer

- Suivre quotidiennement : volume collecté, taux filtré, longueur de la file IA, latence Ollama, taux de JSON valide et part des articles classés `Other`.
- Ajuster les mots-clés et les exceptions de sources à partir du rapport de viabilité.
- Objectif : moins de 100 candidats IA par jour et une file stable sous 50 éléments.

### Phase 2 — Curation de sources

- Ajouter une fiche de source dans l’interface : statut `keep`, `conditional`, `suspend`, raison, volume sur 7/30 jours et dernière réussite.
- Permettre des exceptions nominatives dans `allow_sources` et `block_sources`.
- Réduire progressivement les 293 sources à un noyau validé, sans effacer les sources suspendues.

### Phase 3 — Qualité éditoriale

- Évaluer un échantillon hebdomadaire de fiches Ollama sur exactitude, catégorie, entités et utilité.
- N’utiliser un modèle plus lourd que pour les synthèses de cluster ou les articles à score élevé.
- Mettre en cache les synthèses par empreinte des articles sélectionnés.

### Phase 4 — Workflow final

`source retenue → filtre titre/snippet → extraction → filtre contenu/âge → fiche JSON Ollama → score → cluster → synthèse Ollama des meilleurs clusters → Jarvis Desktop`

Ainsi, Ollama est réservé au traitement et à la rédaction de contenus déjà qualifiés, au lieu de servir de filtre coûteux pour un flux généraliste.

## Contrat de synthèse Jarvis

- `POST /v1/jarvis/query` répond aux recherches, briefings, watchlists et projets avec Ollama et des citations `[1]` liées aux sources retournées.
- Le mode `dashboard` accepte `dashboard_items` (titre, résumé, source, URL, score) pour produire une synthèse de synthèses sans recopier le flux brut.
- Le worker de briefing fabrique un digest sourcé, puis une synthèse exécutive Ollama ; le digest reste conservé sous la synthèse pour audit.
