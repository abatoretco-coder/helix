# News NAS — Architecture complète pour un agent personnel de collecte, extraction, indexation et synthèse de news

## 0. Objectif du projet

Construire une plateforme personnelle, auto-hébergée sur NAS, capable de récupérer un maximum d’informations publiques depuis Internet, de les nettoyer, les stocker, les indexer, les résumer, les classer et les rendre consultables via une interface locale ou une API connectable à Jarvis.

L’objectif n’est pas de créer un simple agrégateur RSS, mais une véritable usine personnelle de news :

```text
Sources → Collecte → Normalisation → Extraction full text → Déduplication
→ Stockage brut → Index recherche → Embeddings → Scoring IA → Résumés
→ Dashboard / Newsletter / API personnelle / Jarvis
```

Le système doit permettre de :

- récupérer massivement des flux RSS, Atom, Google News RSS, Reddit, Hacker News, GitHub, YouTube, sitemaps et pages web ;
- garder une trace des sources, des URLs et des versions brutes ;
- extraire le texte complet des articles ;
- dédupliquer les articles ;
- indexer en full-text ;
- générer des embeddings ;
- classer les articles par thème, source, pays, langue, entités et intérêt personnel ;
- générer des résumés courts et longs ;
- regrouper plusieurs articles parlant du même événement ;
- produire des briefings quotidiens ou hebdomadaires ;
- exposer une API locale pour un dashboard ou Jarvis.

---

## 1. Architecture cible

```text
┌──────────────────────────────────────────────────────────────┐
│                         SOURCES                              │
│ RSS / Atom / Google News RSS / Reddit / HN / GitHub / YouTube │
│ Sites médias / blogs / APIs / sitemaps / pages HTML           │
└───────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                    1. SOURCE REGISTRY                         │
│ sources.yaml + PostgreSQL                                     │
│ Source, type, priorité, fréquence, langue, pays, catégorie    │
└───────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                    2. COLLECTORS                              │
│ RSS / Google News / Reddit / HN / GitHub / YouTube / Sitemap   │
│ Récupération URL + titre + date + snippet + source             │
└───────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                    3. QUEUE                                   │
│ Redis                                                          │
│ Découplage collecte / extraction / IA                          │
└───────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                    4. FULL TEXT EXTRACTION                     │
│ news-please / morss / trafilatura / newspaper / Playwright     │
│ Article complet + titre + auteur + date + langue + image       │
└───────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                    5. RAW DATA LAKE                            │
│ MinIO ou filesystem NAS                                       │
│ HTML brut, JSON brut, payloads, erreurs, logs                  │
└───────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                    6. DATABASE                                │
│ PostgreSQL + pgvector                                          │
│ Articles propres, sources, tags, entités, embeddings           │
└───────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                    7. SEARCH                                  │
│ Meilisearch                                                    │
│ Recherche full-text rapide                                     │
└───────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                    8. AI PIPELINE                              │
│ Ollama / Mistral / Qwen / OpenAI                               │
│ Résumé, traduction, tagging, scoring, clustering               │
└───────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│                    9. INTERFACE                               │
│ FreshRSS + dashboard + newsletter + API Jarvis                 │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Repositories utiles

### 2.1 FreshRSS

Repository :

```bash
https://github.com/FreshRSS/FreshRSS
```

Rôle :

- cockpit RSS ;
- import OPML ;
- supervision humaine des flux ;
- agrégateur local ;
- API RSS ;
- catégories et tags.

Utilisation :

```text
FreshRSS sert de centre de contrôle RSS, mais pas de base finale.
La base finale reste PostgreSQL.
```

---

### 2.2 awesome-rss-feeds

Repository :

```bash
https://github.com/plenaryapp/awesome-rss-feeds
```

Rôle :

- récupérer une liste massive de flux RSS ;
- constituer le premier catalogue de sources ;
- importer dans FreshRSS ;
- alimenter `sources.yaml`.

---

### 2.3 morss

Repository :

```bash
https://github.com/pictuga/morss
```

Rôle :

- transformer des RSS pauvres en RSS enrichis ;
- récupérer plus de texte depuis les liens des flux ;
- convertir certains sites web en flux.

Pipeline :

```text
RSS pauvre → morss → RSS enrichi → collector → extraction → PostgreSQL
```

---

### 2.4 news-please

Repository :

```bash
https://github.com/fhamborg/news-please
```

Rôle :

- crawler et extraire des articles de news ;
- extraire titre, texte, auteur, date, image, langue ;
- utiliser RSS, URLs, sites et archives ;
- exporter en JSON, PostgreSQL, Elasticsearch, Redis.

---

### 2.5 Horizon

Repository :

```bash
https://github.com/Thysrael/Horizon
```

Rôle :

- inspiration pour agent de veille IA ;
- récupération RSS, Hacker News, Reddit, GitHub, Telegram ;
- déduplication ;
- scoring ;
- enrichissement ;
- résumé ;
- briefing quotidien.

---

### 2.6 auto-news

Repository :

```bash
https://github.com/finaldie/auto-news
```

Rôle :

- inspiration pour workflows de résumés ;
- récupération RSS, Reddit, YouTube, articles web ;
- génération de recaps ;
- logique de filtrage par intérêt.

---

### 2.7 trafilatura

Repository :

```bash
https://github.com/adbar/trafilatura
```

Rôle :

- extraction robuste du texte principal ;
- fallback quand news-please échoue ;
- très utile pour articles, blogs et pages web.

---

### 2.8 newspaper4k

Rôle :

- extraction d’articles ;
- titre, texte, auteur, date ;
- fallback simple.

---

### 2.9 Playwright

Rôle :

- rendu navigateur pour sites JavaScript ;
- extraction de pages lourdes ;
- récupération HTML après rendu.

À utiliser en dernier, car coûteux en CPU/RAM.

---

## 3. Stack technique recommandée

```text
Docker Compose
PostgreSQL + pgvector
Redis
MinIO
FreshRSS
Meilisearch
Ollama
FastAPI
Workers Python
Next.js dashboard
```

| Brique | Rôle |
|---|---|
| Docker Compose | Orchestration simple sur NAS |
| PostgreSQL | Base relationnelle principale |
| pgvector | Recherche sémantique locale |
| Redis | Queue légère |
| MinIO | Stockage brut façon S3 |
| FreshRSS | UI et supervision RSS |
| Meilisearch | Recherche full-text rapide |
| Ollama | Résumés, tags, embeddings locaux |
| FastAPI | API pour dashboard et Jarvis |
| Next.js | Dashboard web |
| Python workers | Collecte, extraction, IA, clustering |

---

## 4. Architecture Docker Compose

### 4.1 Services

```text
postgres       → base relationnelle + pgvector
redis          → queue / broker simple
minio          → stockage brut HTML/JSON
freshrss       → cockpit RSS
meilisearch    → moteur de recherche full-text
ollama         → LLM local
api            → API FastAPI
worker_collect → collecte les sources
worker_extract → extrait les articles
worker_ai      → résumé, tags, embeddings, scoring
dashboard      → interface Next.js
```

### 4.2 `docker-compose.yml`

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: news_postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: newsdb
      POSTGRES_USER: news
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    container_name: news_redis
    restart: unless-stopped
    ports:
      - "6379:6379"

  minio:
    image: minio/minio
    container_name: news_minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - ./data/minio:/data
    ports:
      - "9000:9000"
      - "9001:9001"

  freshrss:
    image: freshrss/freshrss:latest
    container_name: news_freshrss
    restart: unless-stopped
    volumes:
      - ./data/freshrss:/var/www/FreshRSS/data
      - ./extensions/freshrss:/var/www/FreshRSS/extensions
    ports:
      - "8080:80"

  meilisearch:
    image: getmeili/meilisearch:latest
    container_name: news_meilisearch
    restart: unless-stopped
    environment:
      MEILI_MASTER_KEY: ${MEILI_MASTER_KEY}
    volumes:
      - ./data/meili:/meili_data
    ports:
      - "7700:7700"

  ollama:
    image: ollama/ollama:latest
    container_name: news_ollama
    restart: unless-stopped
    volumes:
      - ./data/ollama:/root/.ollama
    ports:
      - "11434:11434"

  api:
    build: ./services/api
    container_name: news_api
    restart: unless-stopped
    depends_on:
      - postgres
      - redis
      - meilisearch
      - ollama
    environment:
      DATABASE_URL: postgresql://news:${POSTGRES_PASSWORD}@postgres:5432/newsdb
      REDIS_URL: redis://redis:6379/0
      MEILI_URL: http://meilisearch:7700
      MEILI_MASTER_KEY: ${MEILI_MASTER_KEY}
      OLLAMA_URL: http://ollama:11434
    ports:
      - "8000:8000"

  worker_collect:
    build: ./services/worker
    container_name: news_worker_collect
    restart: unless-stopped
    command: python -m app.workers.collect
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://news:${POSTGRES_PASSWORD}@postgres:5432/newsdb
      REDIS_URL: redis://redis:6379/0

  worker_extract:
    build: ./services/worker
    container_name: news_worker_extract
    restart: unless-stopped
    command: python -m app.workers.extract
    depends_on:
      - postgres
      - redis
      - minio
    environment:
      DATABASE_URL: postgresql://news:${POSTGRES_PASSWORD}@postgres:5432/newsdb
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}

  worker_ai:
    build: ./services/worker
    container_name: news_worker_ai
    restart: unless-stopped
    command: python -m app.workers.ai
    depends_on:
      - postgres
      - redis
      - ollama
    environment:
      DATABASE_URL: postgresql://news:${POSTGRES_PASSWORD}@postgres:5432/newsdb
      REDIS_URL: redis://redis:6379/0
      OLLAMA_URL: http://ollama:11434

  dashboard:
    build: ./dashboard
    container_name: news_dashboard
    restart: unless-stopped
    depends_on:
      - api
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    ports:
      - "3000:3000"
```

### 4.3 `.env`

```env
POSTGRES_PASSWORD=change_me_postgres
MINIO_ROOT_USER=newsminio
MINIO_ROOT_PASSWORD=change_me_minio
MEILI_MASTER_KEY=change_me_meili
```

---

## 5. Structure de projet

```text
helix/
│
├── README.md
├── docker-compose.yml
├── .env
├── .gitignore
│
├── config/
│   ├── sources.yaml
│   ├── topics.yaml
│   ├── scoring_rules.yaml
│   ├── llm_prompts.yaml
│   └── extractor_rules.yaml
│
├── services/
│   ├── api/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app/
│   │       ├── main.py
│   │       ├── routes/
│   │       │   ├── articles.py
│   │       │   ├── sources.py
│   │       │   ├── clusters.py
│   │       │   ├── search.py
│   │       │   └── briefings.py
│   │       ├── db/
│   │       │   ├── session.py
│   │       │   └── models.py
│   │       └── schemas/
│   │
│   ├── worker/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app/
│   │       ├── workers/
│   │       │   ├── collect.py
│   │       │   ├── extract.py
│   │       │   ├── deduplicate.py
│   │       │   ├── embed.py
│   │       │   ├── summarize.py
│   │       │   ├── classify.py
│   │       │   ├── cluster.py
│   │       │   └── newsletter.py
│   │       │
│   │       ├── collectors/
│   │       │   ├── rss.py
│   │       │   ├── google_news.py
│   │       │   ├── reddit.py
│   │       │   ├── hackernews.py
│   │       │   ├── github.py
│   │       │   ├── youtube.py
│   │       │   └── sitemap.py
│   │       │
│   │       ├── extractors/
│   │       │   ├── newsplease.py
│   │       │   ├── morss.py
│   │       │   ├── trafilatura_extractor.py
│   │       │   ├── newspaper_extractor.py
│   │       │   └── playwright_extractor.py
│   │       │
│   │       ├── ai/
│   │       │   ├── summarize.py
│   │       │   ├── classify.py
│   │       │   ├── entities.py
│   │       │   ├── embeddings.py
│   │       │   ├── score.py
│   │       │   └── cluster.py
│   │       │
│   │       ├── storage/
│   │       │   ├── postgres.py
│   │       │   ├── minio.py
│   │       │   ├── redis_queue.py
│   │       │   └── search.py
│   │       │
│   │       └── utils/
│   │           ├── urls.py
│   │           ├── hashing.py
│   │           ├── language.py
│   │           └── logging.py
│
├── dashboard/
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   └── src/
│       ├── app/
│       ├── components/
│       └── lib/
│
├── data/
│   ├── postgres/
│   ├── minio/
│   ├── freshrss/
│   ├── meili/
│   └── ollama/
│
├── scripts/
│   ├── init_db.sql
│   ├── import_sources.py
│   ├── export_opml.py
│   ├── backup.sh
│   └── restore.sh
│
└── docs/
    ├── architecture.md
    ├── roadmap.md
    ├── sources.md
    └── prompts.md
```

---

## 6. Configuration des sources

### 6.1 `config/sources.yaml`

```yaml
sources:
  - name: Hacker News
    type: rss
    url: https://news.ycombinator.com/rss
    category: tech
    language: en
    country: global
    priority: 1
    refresh_minutes: 15
    extraction_strategy: rss_then_article
    enabled: true

  - name: Google News AI France
    type: google_news_rss
    query: "intelligence artificielle"
    language: fr
    country: FR
    category: ai
    priority: 1
    refresh_minutes: 30
    extraction_strategy: article
    enabled: true

  - name: Google News Supply Chain
    type: google_news_rss
    query: "supply chain logistics"
    language: en
    country: global
    category: supply_chain
    priority: 1
    refresh_minutes: 30
    extraction_strategy: article
    enabled: true

  - name: Reddit LocalLLaMA
    type: reddit
    subreddit: LocalLLaMA
    category: ai
    language: en
    country: global
    priority: 2
    refresh_minutes: 30
    extraction_strategy: reddit
    enabled: true

  - name: GitHub Trending AI
    type: github_trending
    topic: artificial-intelligence
    language: en
    country: global
    category: tech
    priority: 2
    refresh_minutes: 360
    extraction_strategy: github
    enabled: true

  - name: YouTube Example Channel
    type: youtube_channel
    channel_id: UCxxxxxxxxxxxxxxxx
    category: tech
    language: en
    country: global
    priority: 3
    refresh_minutes: 360
    extraction_strategy: youtube
    enabled: false

  - name: Example Sitemap
    type: sitemap
    url: https://example.com/sitemap.xml
    category: general
    language: en
    country: global
    priority: 3
    refresh_minutes: 720
    extraction_strategy: article
    enabled: false
```

### 6.2 Types de sources

```text
rss
atom
google_news_rss
reddit
hackernews
github_releases
github_trending
youtube_channel
sitemap
html_page
custom_api
```

### 6.3 Fréquences recommandées

```text
Priorité 1 — toutes les 15 à 30 minutes
- breaking news
- Google News RSS
- Hacker News
- Reddit important
- sources tech majeures

Priorité 2 — toutes les 1 à 3 heures
- blogs
- médias spécialisés
- GitHub
- YouTube

Priorité 3 — 1 fois par jour
- rapports
- institutions
- think tanks
- newsletters archivées
- sitemaps lourds

Priorité 4 — 1 fois par semaine
- archives
- sources lentes
- deep crawl
```

---

## 7. Sources à récupérer

### 7.1 RSS / Atom

Sources prioritaires :

```text
- médias généralistes ;
- presse économique ;
- presse tech ;
- blogs spécialisés ;
- médias locaux ;
- institutions ;
- gouvernements ;
- think tanks ;
- chaînes YouTube avec RSS ;
- GitHub releases ;
- blogs d’entreprises ;
- sites scientifiques ;
- flux cyber sécurité.
```

### 7.2 Google News RSS

Exemples de thèmes :

```text
artificial intelligence
local llm
open source ai
supply chain
logistics
pharma distribution
warehouse automation
transport decarbonization
carbon accounting
European regulation
geopolitics
France logistics
Canada travel
startups
SaaS
robotics
```

URL générique FR :

```text
https://news.google.com/rss/search?q=<QUERY>&hl=fr&gl=FR&ceid=FR:fr
```

URL générique EN :

```text
https://news.google.com/rss/search?q=<QUERY>&hl=en-US&gl=US&ceid=US:en
```

### 7.3 Reddit

Subreddits utiles :

```text
r/worldnews
r/europe
r/france
r/technology
r/MachineLearning
r/LocalLLaMA
r/selfhosted
r/programming
r/supplychain
r/logistics
r/startups
r/SaaS
r/cybersecurity
r/dataengineering
```

### 7.4 Hacker News

RSS simple :

```text
https://news.ycombinator.com/rss
```

API avancée :

```text
topstories
newstories
beststories
askstories
showstories
jobstories
```

### 7.5 GitHub

À récupérer :

```text
- releases de repos suivis ;
- trending repos ;
- topics GitHub ;
- repo search ;
- issues populaires ;
- pull requests ;
- stars récentes ;
- commits sur repos stratégiques.
```

Topics utiles :

```text
ai
llm
rag
agents
scraper
rss
news
automation
vector-database
self-hosted
fastapi
nextjs
ollama
postgres
pgvector
```

### 7.6 YouTube

RSS par chaîne :

```text
https://www.youtube.com/feeds/videos.xml?channel_id=<CHANNEL_ID>
```

À récupérer :

```text
- titre vidéo ;
- description ;
- date ;
- chaîne ;
- URL ;
- transcript si disponible ;
- résumé IA ;
- tags ;
- score d’intérêt.
```

### 7.7 Sitemaps

À tester :

```text
/sitemap.xml
/news-sitemap.xml
/sitemap_index.xml
/sitemap-news.xml
```

Rôle :

```text
- détecter les nouvelles URLs ;
- éviter un crawl trop brutal ;
- récupérer des articles sans RSS ;
- compléter les sources.
```

### 7.8 Pages HTML sans RSS

Fallback :

```text
1. requests + trafilatura
2. news-please
3. newspaper4k
4. Playwright
```

---

## 8. Pipeline de traitement

### 8.1 Collecte légère

Données collectées :

```text
URL
titre
source
date de publication
date de découverte
snippet
type de source
raw payload
```

Statuts possibles :

```text
new
queued_for_extraction
extracted
failed
duplicate
ignored
queued_for_ai
ai_processed
clustered
```

### 8.2 Normalisation URL

Nettoyage :

```text
- suppression des paramètres UTM ;
- suppression de fbclid, gclid ;
- suppression des fragments # ;
- normalisation du trailing slash ;
- lower-case du domaine ;
- canonical URL si disponible ;
- hash de l’URL nettoyée.
```

Pseudo-code :

```python
def normalize_url(url: str) -> str:
    """
    Normalize URL by removing tracking parameters and fragments.
    """
    tracking_params = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "fbclid", "gclid", "mc_cid", "mc_eid"
    }
    # parse URL
    # remove tracking params
    # remove fragment
    # normalize scheme/domain
    # return cleaned URL
```

### 8.3 Déduplication

Niveaux :

```text
1. Même URL nettoyée
2. Même canonical URL
3. Même hash de contenu
4. Titre très proche + même fenêtre temporelle + mêmes entités
5. Embedding proche + publication proche dans le temps
```

### 8.4 Extraction full text

Ordre recommandé :

```text
1. RSS content si contenu complet
2. morss si RSS tronqué
3. news-please
4. trafilatura
5. newspaper4k
6. Playwright si site JavaScript
```

Données extraites :

```text
title
description
text_content
author
published_at
language
image_url
top_image
keywords
word_count
raw_html_path
extraction_status
extractor_used
```

### 8.5 Stockage brut

Stockage dans MinIO :

```text
/raw_html/YYYY/MM/DD/source/article_id.html
/raw_json/YYYY/MM/DD/source/article_id.json
/rss_payload/YYYY/MM/DD/source/item_id.json
/screenshots/YYYY/MM/DD/source/article_id.png
/errors/YYYY/MM/DD/source/article_id.json
```

### 8.6 Scoring qualité

Critères :

```text
+ texte > 500 mots
+ titre présent
+ date présente
+ auteur présent
+ image présente
+ langue détectée
+ source fiable
- texte trop court
- contenu répété
- beaucoup de menus/cookies
- langue incohérente
- extraction échouée
- contenu probablement dupliqué
```

Pseudo-code :

```python
def compute_quality_score(article):
    score = 0

    if article.title:
        score += 10
    if article.text_content and len(article.text_content) > 1000:
        score += 30
    if article.published_at:
        score += 10
    if article.author:
        score += 5
    if article.image_url:
        score += 5
    if article.word_count and article.word_count > 500:
        score += 20
    if article.language:
        score += 10

    return min(score, 100)
```

### 8.7 Enrichissement IA

Pour chaque article propre :

```text
- résumé court ;
- résumé long ;
- catégories ;
- tags ;
- entités ;
- sentiment ;
- score d’importance ;
- score de nouveauté ;
- score d’intérêt personnel ;
- embedding ;
- langue ;
- pays mentionnés ;
- entreprises mentionnées ;
- personnes mentionnées.
```

### 8.8 Clustering

Objectif :

```text
Regrouper plusieurs articles qui parlent du même événement.
```

Critères :

```text
- similarité titre ;
- similarité embedding ;
- mêmes entités ;
- même fenêtre temporelle ;
- même sujet ;
- même événement.
```

### 8.9 Briefing

Sorties :

```text
- top 10 news du jour ;
- top news par catégorie ;
- briefing IA ;
- briefing supply chain ;
- briefing tech ;
- briefing géopolitique ;
- résumé hebdomadaire ;
- alertes sur mots-clés ;
- API Jarvis.
```

---

## 9. Schéma PostgreSQL

### 9.1 Extension pgvector

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 9.2 Table `sources`

```sql
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    url TEXT,
    query TEXT,
    country TEXT,
    language TEXT,
    category TEXT,
    priority INTEGER DEFAULT 3,
    refresh_minutes INTEGER DEFAULT 60,
    extraction_strategy TEXT DEFAULT 'article',
    enabled BOOLEAN DEFAULT TRUE,
    last_checked_at TIMESTAMP,
    last_success_at TIMESTAMP,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 9.3 Table `raw_items`

```sql
CREATE TABLE raw_items (
    id BIGSERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    url TEXT NOT NULL,
    normalized_url TEXT,
    canonical_url TEXT,
    title TEXT,
    snippet TEXT,
    published_at TIMESTAMP,
    discovered_at TIMESTAMP DEFAULT NOW(),
    raw_payload JSONB,
    status TEXT DEFAULT 'new',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(normalized_url)
);
```

### 9.4 Table `articles`

```sql
CREATE TABLE articles (
    id BIGSERIAL PRIMARY KEY,
    raw_item_id BIGINT REFERENCES raw_items(id),
    source_id INTEGER REFERENCES sources(id),
    url TEXT NOT NULL,
    normalized_url TEXT,
    canonical_url TEXT,
    title TEXT,
    description TEXT,
    text_content TEXT,
    author TEXT,
    language TEXT,
    published_at TIMESTAMP,
    discovered_at TIMESTAMP,
    extracted_at TIMESTAMP DEFAULT NOW(),
    image_url TEXT,
    top_image_url TEXT,
    word_count INTEGER,
    content_hash TEXT,
    quality_score NUMERIC,
    extractor_used TEXT,
    raw_html_path TEXT,
    raw_json_path TEXT,
    extraction_status TEXT DEFAULT 'success',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(content_hash)
);
```

### 9.5 Table `article_ai`

```sql
CREATE TABLE article_ai (
    article_id BIGINT PRIMARY KEY REFERENCES articles(id),
    summary_short TEXT,
    summary_long TEXT,
    category TEXT,
    topics TEXT[],
    entities JSONB,
    sentiment TEXT,
    importance_score NUMERIC,
    novelty_score NUMERIC,
    personal_relevance_score NUMERIC,
    final_score NUMERIC,
    embedding VECTOR(768),
    model_name TEXT,
    processed_at TIMESTAMP DEFAULT NOW()
);
```

### 9.6 Table `clusters`

```sql
CREATE TABLE clusters (
    id BIGSERIAL PRIMARY KEY,
    main_title TEXT,
    main_summary TEXT,
    topic TEXT,
    language TEXT,
    first_seen_at TIMESTAMP,
    last_seen_at TIMESTAMP,
    article_count INTEGER DEFAULT 0,
    importance_score NUMERIC,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 9.7 Table `article_clusters`

```sql
CREATE TABLE article_clusters (
    article_id BIGINT REFERENCES articles(id),
    cluster_id BIGINT REFERENCES clusters(id),
    similarity_score NUMERIC,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY(article_id, cluster_id)
);
```

### 9.8 Table `processing_logs`

```sql
CREATE TABLE processing_logs (
    id BIGSERIAL PRIMARY KEY,
    item_type TEXT NOT NULL,
    item_id BIGINT,
    step TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 9.9 Index

```sql
CREATE INDEX idx_sources_enabled ON sources(enabled);
CREATE INDEX idx_sources_priority ON sources(priority);
CREATE INDEX idx_raw_items_status ON raw_items(status);
CREATE INDEX idx_raw_items_published_at ON raw_items(published_at);
CREATE INDEX idx_articles_published_at ON articles(published_at);
CREATE INDEX idx_articles_language ON articles(language);
CREATE INDEX idx_articles_source_id ON articles(source_id);
CREATE INDEX idx_articles_quality_score ON articles(quality_score);
CREATE INDEX idx_article_ai_final_score ON article_ai(final_score);
CREATE INDEX idx_clusters_last_seen_at ON clusters(last_seen_at);
```

Index vectoriel :

```sql
CREATE INDEX idx_article_ai_embedding
ON article_ai
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

---

## 10. Workers

### 10.1 Worker collect

Rôle :

```text
- lire sources.yaml ou table sources ;
- identifier les sources à rafraîchir ;
- appeler le bon collector ;
- insérer dans raw_items ;
- pousser les nouveaux items dans Redis.
```

Pseudo-code :

```python
def collect_worker():
    sources = get_due_sources()

    for source in sources:
        try:
            items = collect_source(source)

            for item in items:
                normalized_url = normalize_url(item.url)

                if not raw_item_exists(normalized_url):
                    raw_item = insert_raw_item(source, item, normalized_url)
                    enqueue("extract", raw_item.id)

            mark_source_success(source)

        except Exception as exc:
            mark_source_error(source, str(exc))
```

### 10.2 Worker extract

Rôle :

```text
- lire les raw_items en attente ;
- récupérer l’URL ;
- extraire le contenu complet ;
- stocker le HTML brut ;
- insérer dans articles ;
- pousser vers queue IA.
```

Pseudo-code :

```python
def extract_worker():
    while True:
        job = dequeue("extract")
        raw_item = get_raw_item(job.id)

        try:
            article = extract_article(raw_item.url)
            html_path = store_raw_html(article.raw_html)
            content_hash = hash_content(article.text_content)

            if article_exists_by_hash(content_hash):
                mark_raw_item_duplicate(raw_item)
                continue

            article_id = insert_article(
                raw_item=raw_item,
                article=article,
                html_path=html_path,
                content_hash=content_hash,
            )

            enqueue("ai", article_id)
            mark_raw_item_extracted(raw_item)

        except Exception as exc:
            mark_raw_item_failed(raw_item, str(exc))
```

### 10.3 Worker AI

Rôle :

```text
- résumer ;
- classer ;
- extraire les entités ;
- générer embeddings ;
- calculer scoring ;
- indexer dans Meilisearch ;
- pousser vers clustering.
```

Pseudo-code :

```python
def ai_worker():
    while True:
        job = dequeue("ai")
        article = get_article(job.article_id)

        summary_short = summarize_short(article)
        summary_long = summarize_long(article)
        category = classify_article(article)
        entities = extract_entities(article)
        embedding = generate_embedding(article)
        scores = compute_scores(article, category, entities)

        save_article_ai(
            article_id=article.id,
            summary_short=summary_short,
            summary_long=summary_long,
            category=category,
            entities=entities,
            embedding=embedding,
            scores=scores,
        )

        index_article_in_search(article, summary_short, category, entities, scores)
        enqueue("cluster", article.id)
```

### 10.4 Worker cluster

Rôle :

```text
- trouver les articles proches ;
- créer ou mettre à jour un cluster ;
- générer un résumé de cluster ;
- mettre à jour l’importance du cluster.
```

Pseudo-code :

```python
def cluster_worker():
    while True:
        job = dequeue("cluster")
        article = get_article_with_ai(job.article_id)

        candidates = find_similar_articles(
            embedding=article.embedding,
            published_window_hours=72,
            min_similarity=0.88,
        )

        cluster = find_best_cluster(candidates)

        if cluster:
            attach_article_to_cluster(article, cluster)
            update_cluster_summary(cluster)
        else:
            create_cluster_from_article(article)
```

---

## 11. Collectors

### 11.1 RSS collector

Librairie :

```bash
pip install feedparser
```

Pseudo-code :

```python
import feedparser

def collect_rss(source):
    feed = feedparser.parse(source.url)
    items = []

    for entry in feed.entries:
        items.append({
            "title": entry.get("title"),
            "url": entry.get("link"),
            "snippet": entry.get("summary"),
            "published_at": entry.get("published"),
            "raw_payload": dict(entry),
        })

    return items
```

### 11.2 Google News RSS collector

Rôle :

```text
- construire une URL Google News RSS depuis query/pays/langue ;
- parser comme RSS classique ;
- extraire les URLs d’articles.
```

URL exemple :

```text
https://news.google.com/rss/search?q=supply%20chain&hl=en-US&gl=US&ceid=US:en
```

### 11.3 Reddit collector

Options :

```text
- RSS Reddit simple ;
- API Reddit ;
- PRAW si besoin.
```

RSS subreddit :

```text
https://www.reddit.com/r/LocalLLaMA/.rss
```

### 11.4 Hacker News collector

RSS simple :

```text
https://news.ycombinator.com/rss
```

API avancée :

```text
https://hacker-news.firebaseio.com/v0/topstories.json
```

### 11.5 GitHub collector

Types :

```text
- releases ;
- trending ;
- topics ;
- repo search ;
- issues ;
- pull requests.
```

### 11.6 YouTube collector

RSS :

```text
https://www.youtube.com/feeds/videos.xml?channel_id=<CHANNEL_ID>
```

### 11.7 Sitemap collector

Rôle :

```text
- lire sitemap.xml ;
- récupérer les URLs ;
- filtrer par date si disponible ;
- pousser vers extraction.
```

---

## 12. Extractors

### 12.1 Stratégie

```text
1. RSS content si contenu complet
2. morss si RSS partiel
3. news-please
4. trafilatura
5. newspaper4k
6. Playwright
```

### 12.2 Interface cible

```python
class ExtractedArticle:
    url: str
    title: str
    description: str
    text_content: str
    author: str
    published_at: str
    language: str
    image_url: str
    raw_html: str
    extractor_used: str
```

### 12.3 Playwright

À utiliser uniquement si :

```text
- HTML statique insuffisant ;
- contenu injecté par JavaScript ;
- site stratégique.
```

Limite recommandée :

```text
max_concurrent_browsers: 1
timeout_seconds: 30
```

---

## 13. IA locale

### 13.1 Ollama

Usage :

```text
- résumé court ;
- résumé long ;
- classification ;
- extraction d’entités ;
- scoring ;
- traduction ;
- génération de briefing ;
- embeddings si modèle compatible.
```

Modèles possibles :

```text
llama3.1
mistral
qwen2.5
phi
nomic-embed-text
bge-m3
```

### 13.2 Prompts

Fichier :

```text
config/llm_prompts.yaml
```

Exemple :

```yaml
summarize_short: |
  You are a news summarization assistant.
  Summarize the article in 3 concise bullet points.
  Keep facts precise.
  Do not invent information.

summarize_long: |
  Summarize the article in 10 lines maximum.
  Include:
  - main event
  - actors involved
  - location
  - date if available
  - potential impact

classify: |
  Classify the article into one main category:
  - AI
  - Supply Chain
  - Pharma
  - Logistics
  - Geopolitics
  - Regulation
  - Tech
  - Climate
  - Finance
  - Other

extract_entities: |
  Extract named entities from the article.
  Return JSON with:
  - people
  - companies
  - countries
  - cities
  - products
  - regulations
  - technologies
```

### 13.3 Catégories recommandées

```yaml
categories:
  - AI
  - Local LLM
  - Agents
  - Supply Chain
  - Pharma Logistics
  - Transport
  - Carbon Accounting
  - Warehouse Automation
  - Robotics
  - SaaS
  - Startups
  - Cybersecurity
  - Geopolitics
  - European Regulation
  - Climate
  - Finance
  - Travel
  - Culture
  - Other
```

### 13.4 Scoring personnel

Fichier :

```text
config/scoring_rules.yaml
```

Exemple :

```yaml
interests:
  artificial intelligence: 1.0
  local llm: 1.0
  supply chain: 0.95
  pharma logistics: 0.95
  transport decarbonization: 0.9
  carbon accounting: 0.85
  warehouse automation: 0.85
  robotics: 0.8
  startups: 0.75
  saas: 0.75
  geopolitics: 0.7
  european regulation: 0.7
  travel canada: 0.5

source_weights:
  official: 1.0
  major_media: 0.9
  niche_blog: 0.7
  reddit: 0.6
  hackernews: 0.7
  github: 0.8

freshness:
  less_than_6h: 1.0
  less_than_24h: 0.9
  less_than_72h: 0.7
  less_than_7d: 0.4
  older: 0.2
```

Score final :

```text
final_score =
  source_score * 0.20
+ freshness_score * 0.20
+ topic_interest_score * 0.25
+ novelty_score * 0.20
+ engagement_score * 0.10
+ quality_score * 0.05
```

---

## 14. Recherche

### 14.1 Meilisearch

Index :

```text
articles
clusters
sources
briefings
```

Champs indexés :

```text
title
summary_short
summary_long
text_content
source
category
topics
entities
language
country
published_at
final_score
```

Filtres :

```text
source
category
language
country
published_at
final_score
quality_score
cluster_id
```

### 14.2 Recherche sémantique avec pgvector

```sql
SELECT
    a.id,
    a.title,
    ai.summary_short,
    ai.embedding <=> $1 AS distance
FROM article_ai ai
JOIN articles a ON a.id = ai.article_id
ORDER BY ai.embedding <=> $1
LIMIT 10;
```

---

## 15. API FastAPI

### 15.1 Endpoints

```text
GET /health
GET /sources
POST /sources
PATCH /sources/{id}
GET /articles
GET /articles/{id}
GET /articles/search?q=
GET /clusters
GET /clusters/{id}
GET /briefings/daily
POST /briefings/generate
POST /admin/reprocess/{article_id}
POST /admin/reindex
POST /admin/import-sources
POST /jarvis/query
```

### 15.2 Exemple de réponse article

```json
{
  "id": 123,
  "title": "Example news title",
  "url": "https://example.com/article",
  "source": "Example Source",
  "published_at": "2026-06-12T08:00:00",
  "language": "en",
  "category": "AI",
  "summary_short": "Short summary here.",
  "topics": ["AI", "Agents"],
  "entities": {
    "companies": ["OpenAI"],
    "countries": ["United States"]
  },
  "quality_score": 87,
  "final_score": 0.91
}
```

---

## 16. Dashboard Next.js

### 16.1 Pages

```text
/dashboard
  Vue du jour : top news, clusters, sujets chauds

/sources
  Liste des sources, statut, erreurs, fréquence

/articles
  Recherche, filtres, tags, langue, pays

/articles/[id]
  Article complet, résumé, source, contenu brut, liens

/clusters
  Même événement vu par plusieurs sources

/clusters/[id]
  Résumé de l’événement + articles liés

/topics
  IA, supply chain, pharma, tech, géopolitique, etc.

/briefings
  Briefing quotidien, hebdo, mensuel

/admin
  Relancer extraction, désactiver source, voir logs
```

### 16.2 Filtres

```text
- date ;
- source ;
- pays ;
- langue ;
- catégorie ;
- score ;
- lu / non lu ;
- résumé disponible ;
- contenu complet disponible ;
- cluster ;
- entités ;
- qualité extraction ;
- extractor utilisé.
```

### 16.3 Composants

```text
ArticleCard
SourceStatusCard
ClusterCard
ScoreBadge
TopicBadge
SearchBar
DateFilter
CategoryFilter
SourceFilter
BriefingPanel
AdminJobPanel
```

---

## 17. Connexion Jarvis

### 17.1 Cas d’usage

```text
"Donne-moi les 10 news IA importantes d’aujourd’hui"
"Qu’est-ce qui a bougé en supply chain pharma cette semaine ?"
"Résume-moi les news sur OpenAI, NVIDIA et réglementation européenne"
"Compare les sources françaises et américaines sur ce sujet"
"Quels nouveaux repos GitHub IA ont explosé cette semaine ?"
"Prépare-moi un briefing vocal de 2 minutes"
```

### 17.2 Endpoint

```text
POST /jarvis/query
```

Payload :

```json
{
  "query": "Quelles sont les principales news IA aujourd'hui ?",
  "date_range": "today",
  "categories": ["AI"],
  "limit": 10
}
```

Réponse :

```json
{
  "answer": "Voici les principales news IA du jour...",
  "articles": [
    {
      "title": "...",
      "summary": "...",
      "url": "...",
      "source": "..."
    }
  ]
}
```

---

## 18. Monitoring

### 18.1 Logs à suivre

```text
- nombre de sources actives ;
- nombre d’items collectés par heure ;
- taux d’extraction réussie ;
- taux d’échec par source ;
- nombre de doublons ;
- temps moyen extraction ;
- temps moyen résumé IA ;
- taille PostgreSQL ;
- taille MinIO ;
- latence Meilisearch ;
- RAM/CPU Ollama.
```

### 18.2 Métriques

```text
sources_active_total
raw_items_collected_total
articles_extracted_total
articles_failed_total
duplicates_detected_total
ai_processed_total
clusters_created_total
queue_size_extract
queue_size_ai
avg_extraction_time_seconds
avg_ai_time_seconds
```

### 18.3 Outils possibles

MVP :

```text
logs Docker + table processing_logs
```

Plus tard :

```text
Prometheus
Grafana
Loki
Uptime Kuma
```

---

## 19. Backup

### 19.1 Données à sauvegarder

```text
./data/postgres
./data/minio
./data/freshrss
./data/meili
./config
.env
```

### 19.2 Script backup

```bash
#!/bin/bash

DATE=$(date +"%Y-%m-%d_%H-%M")
BACKUP_DIR="./backups/$DATE"

mkdir -p "$BACKUP_DIR"

docker exec news_postgres pg_dump -U news newsdb > "$BACKUP_DIR/newsdb.sql"

tar -czf "$BACKUP_DIR/config.tar.gz" ./config
tar -czf "$BACKUP_DIR/freshrss.tar.gz" ./data/freshrss

echo "Backup completed: $BACKUP_DIR"
```

---

## 20. Roadmap de build

### Phase 1 — Socle technique

Objectif :

```text
Avoir une stack locale fonctionnelle.
```

Tâches :

```text
- créer repo news-nas ;
- créer docker-compose.yml ;
- lancer PostgreSQL ;
- lancer Redis ;
- lancer FreshRSS ;
- lancer Meilisearch ;
- lancer MinIO ;
- créer .env ;
- créer README ;
- créer scripts/init_db.sql.
```

Livrable :

```text
docker compose up -d fonctionne.
```

### Phase 2 — Database

Objectif :

```text
Créer le modèle de données.
```

Tâches :

```text
- créer extension pgvector ;
- créer tables sources ;
- créer raw_items ;
- créer articles ;
- créer article_ai ;
- créer clusters ;
- créer article_clusters ;
- créer processing_logs ;
- créer index.
```

### Phase 3 — Source registry

Objectif :

```text
Définir les sources.
```

Tâches :

```text
- créer config/sources.yaml ;
- ajouter 20 sources de test ;
- ajouter Google News RSS IA ;
- ajouter Google News RSS supply chain ;
- ajouter Hacker News ;
- ajouter Reddit LocalLLaMA ;
- créer script import_sources.py ;
- insérer les sources dans PostgreSQL.
```

### Phase 4 — Collector RSS

Objectif :

```text
Collecter les premiers items.
```

Tâches :

```text
- installer feedparser ;
- coder collectors/rss.py ;
- coder normalize_url ;
- insérer raw_items ;
- gérer doublons URL ;
- gérer erreurs ;
- log processing_logs.
```

### Phase 5 — Queue Redis

Objectif :

```text
Découpler collecte et extraction.
```

Tâches :

```text
- créer redis_queue.py ;
- créer queue extract ;
- pousser raw_item_id ;
- lire depuis worker_extract ;
- gérer retry.
```

### Phase 6 — Extraction article

Objectif :

```text
Extraire le texte complet.
```

Tâches :

```text
- intégrer trafilatura ;
- intégrer news-please ;
- coder extract_article ;
- stocker raw HTML dans MinIO ;
- calculer content_hash ;
- insérer articles ;
- mettre statut raw_items à extracted.
```

### Phase 7 — Recherche full-text

Objectif :

```text
Rechercher les articles rapidement.
```

Tâches :

```text
- créer index Meilisearch articles ;
- indexer title, summary, text ;
- endpoint GET /articles/search ;
- filtres source/catégorie/langue/date.
```

### Phase 8 — IA locale

Objectif :

```text
Résumer et classer les articles.
```

Tâches :

```text
- lancer Ollama ;
- télécharger modèle LLM ;
- télécharger modèle embedding ;
- coder summarize_short ;
- coder classify_article ;
- coder extract_entities ;
- coder generate_embedding ;
- insérer article_ai.
```

### Phase 9 — Scoring

Objectif :

```text
Prioriser les articles intéressants.
```

Tâches :

```text
- créer scoring_rules.yaml ;
- coder quality_score ;
- coder freshness_score ;
- coder source_score ;
- coder topic_interest_score ;
- coder final_score.
```

### Phase 10 — Clustering

Objectif :

```text
Regrouper les mêmes événements.
```

Tâches :

```text
- recherche similarité embedding ;
- fenêtre temporelle 72h ;
- création clusters ;
- association article_clusters ;
- résumé de cluster.
```

### Phase 11 — API

Objectif :

```text
Exposer les données.
```

Tâches :

```text
- FastAPI ;
- endpoints sources ;
- endpoints articles ;
- endpoints search ;
- endpoints clusters ;
- endpoint briefing ;
- endpoint admin reprocess.
```

### Phase 12 — Dashboard

Objectif :

```text
Interface de lecture et pilotage.
```

Tâches :

```text
- Next.js ;
- page dashboard ;
- page articles ;
- page sources ;
- page clusters ;
- page briefings ;
- filtres ;
- recherche.
```

### Phase 13 — Briefing agent

Objectif :

```text
Générer des synthèses quotidiennes.
```

Tâches :

```text
- sélectionner top articles ;
- regrouper par cluster ;
- générer briefing ;
- sauvegarder briefing ;
- endpoint /briefings/daily.
```

### Phase 14 — Jarvis

Objectif :

```text
Connecter la base news à Jarvis.
```

Tâches :

```text
- endpoint /jarvis/query ;
- recherche sémantique ;
- génération réponse ;
- liens sources ;
- résumé vocal possible.
```

---

## 21. Backlog

### Must have

```text
- Docker Compose
- PostgreSQL
- Redis
- FreshRSS
- sources.yaml
- RSS collector
- Google News RSS collector
- URL normalization
- raw_items
- article extraction
- articles table
- MinIO raw HTML
- Meilisearch index
- FastAPI search endpoint
```

### Should have

```text
- Ollama summarization
- article classification
- embeddings
- pgvector semantic search
- scoring
- dashboard simple
- clusters
- daily briefing
```

### Could have

```text
- Reddit collector
- HN advanced collector
- GitHub trending collector
- YouTube transcript
- Playwright fallback
- newsletter email
- Discord/Telegram alerting
- Grafana monitoring
```

### Later

```text
- multi-user
- mobile app
- voice briefing
- fine-tuned scoring
- source reliability scoring
- trend detection
- timeline by topic
- automatic source discovery
- browser extension save-to-newsbase
```

---

## 22. Commandes de démarrage

### 22.1 Créer le repo

```bash
mkdir news-nas
cd news-nas
git init
```

### 22.2 Créer les dossiers

```bash
mkdir -p config
mkdir -p services/api/app
mkdir -p services/worker/app
mkdir -p dashboard
mkdir -p data/postgres data/minio data/freshrss data/meili data/ollama
mkdir -p scripts docs backups
```

### 22.3 Lancer la stack

```bash
docker compose up -d
```

### 22.4 Vérifier les services

```bash
docker ps
```

URLs locales :

```text
FreshRSS      http://localhost:8080
MinIO         http://localhost:9001
Meilisearch   http://localhost:7700
Ollama        http://localhost:11434
API           http://localhost:8000
Dashboard     http://localhost:3000
```

---

## 23. Requirements Python

### 23.1 Worker

Fichier :

```text
services/worker/requirements.txt
```

```txt
feedparser
requests
httpx
beautifulsoup4
lxml
trafilatura
newspaper4k
redis
psycopg2-binary
sqlalchemy
pydantic
python-dotenv
pyyaml
minio
meilisearch
langdetect
python-dateutil
tenacity
```

Optionnel :

```txt
playwright
news-please
praw
youtube-transcript-api
```

### 23.2 API

Fichier :

```text
services/api/requirements.txt
```

```txt
fastapi
uvicorn
psycopg2-binary
sqlalchemy
pydantic
python-dotenv
redis
meilisearch
pyyaml
httpx
```

---

## 24. Dockerfiles

### 24.1 Worker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

CMD ["python", "-m", "app.workers.collect"]
```

### 24.2 API

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 25. Règles opérationnelles

Même pour un usage personnel, il faut éviter de saturer le NAS ou de se faire bloquer inutilement.

Recommandations :

```text
- limiter la concurrence ;
- mettre des timeouts ;
- mettre des retries propres ;
- stocker les erreurs ;
- désactiver automatiquement les sources qui échouent trop ;
- ne pas utiliser Playwright par défaut ;
- ne pas crawler tout un domaine sans limite ;
- privilégier RSS, sitemaps, APIs publiques.
```

Paramètres recommandés :

```yaml
crawler:
  max_concurrent_requests: 5
  request_timeout_seconds: 20
  max_retries: 3
  user_agent: "PersonalNewsBot/0.1"
  min_delay_between_requests_seconds: 2

playwright:
  enabled: true
  max_concurrent_browsers: 1
  timeout_seconds: 30

extraction:
  min_word_count: 150
  max_article_length_chars: 100000
```

---

## 26. Limites NAS à anticiper

### 26.1 CPU/RAM

Attention avec :

```text
- Playwright ;
- gros LLM Ollama ;
- embeddings massifs ;
- extraction parallèle ;
- indexation massive.
```

Recommandation :

```text
Commencer avec 2 à 4 workers max.
```

### 26.2 Stockage

Le HTML brut peut grossir vite.

Stratégie :

```text
- garder HTML brut 90 jours ;
- garder JSON propre indéfiniment ;
- compresser les anciens fichiers ;
- archiver les screenshots ;
- supprimer les pages failed inutiles après 30 jours.
```

### 26.3 Base de données

Prévoir :

```text
- index propres ;
- nettoyage des raw_items échoués ;
- partitionnement plus tard si énorme volume ;
- backup régulier.
```

---

## 27. MVP recommandé

Objectif MVP :

```text
- récupérer 100 à 500 flux ;
- extraire les articles ;
- stocker dans PostgreSQL ;
- indexer dans Meilisearch ;
- générer un résumé court ;
- afficher les top news du jour.
```

MVP stack :

```text
PostgreSQL
Redis
FreshRSS
Meilisearch
Ollama
FastAPI
Worker Python
```

Exclusions temporaires :

```text
- pas de Playwright au début ;
- pas de YouTube transcript au début ;
- pas de clustering complexe au début ;
- pas de dashboard avancé au début ;
- pas de multi-user.
```

---

## 28. Première version ultra concrète

### Jour 1

```text
- créer repo ;
- docker-compose ;
- lancer PostgreSQL, Redis, FreshRSS ;
- créer tables ;
- créer sources.yaml ;
- importer 20 sources.
```

### Jour 2

```text
- coder RSS collector ;
- collecter raw_items ;
- normaliser URLs ;
- gérer doublons.
```

### Jour 3

```text
- coder extractor trafilatura ;
- intégrer news-please ensuite ;
- insérer articles ;
- stocker HTML brut.
```

### Jour 4

```text
- ajouter Meilisearch ;
- indexer articles ;
- créer API search.
```

### Jour 5

```text
- ajouter Ollama ;
- résumer les articles ;
- classer les articles ;
- afficher top articles.
```

---

## 29. Définition du succès

Le projet est réussi quand tu peux demander :

```text
"Quelles sont les principales news IA aujourd’hui ?"
```

Et obtenir :

```text
- une synthèse propre ;
- les événements regroupés ;
- les sources d’origine ;
- les liens ;
- les dates ;
- les résumés ;
- un score d’importance ;
- une recherche possible dans l’historique.
```

---

## 30. Prochaine étape de codage

Commencer par ce squelette :

```text
helix/
├── docker-compose.yml
├── .env
├── config/sources.yaml
├── scripts/init_db.sql
├── services/worker/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── workers/collect.py
│       ├── collectors/rss.py
│       ├── storage/postgres.py
│       └── utils/urls.py
└── services/api/
    ├── Dockerfile
    ├── requirements.txt
    └── app/main.py
```

Première fonctionnalité à coder :

```text
sources.yaml → RSS collector → raw_items PostgreSQL
```

Ensuite :

```text
raw_items → extraction article → articles PostgreSQL
```

Puis :

```text
articles → Meilisearch → API search
```

Puis :

```text
articles → Ollama → article_ai
```

---

## 31. Résumé final

Architecture finale :

```text
FreshRSS
+ sources.yaml
+ collectors Python
+ Redis queue
+ news-please
+ morss
+ trafilatura
+ MinIO
+ PostgreSQL
+ pgvector
+ Meilisearch
+ Ollama
+ FastAPI
+ Next.js
+ Jarvis
```

Le NAS devient une base de connaissance vivante :

```text
- il aspire Internet par flux ;
- il stocke les articles ;
- il garde le brut ;
- il nettoie les textes ;
- il comprend les sujets ;
- il résume ;
- il détecte les tendances ;
- il regroupe les événements ;
- il alimente Jarvis ;
- il produit des briefings automatiques.
```
