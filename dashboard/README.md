# News NAS Dashboard

Next.js 14 frontend for the News NAS platform.

## Development

```bash
npm install
npm run dev
```

Open http://localhost:3000

## Build

```bash
npm run build
npm start
```

## Docker

```bash
docker build -t news-nas-dashboard .
docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://api:8000 news-nas-dashboard
```

## Environment Variables

- `NEXT_PUBLIC_API_URL` - FastAPI base URL (default: http://localhost:8000)

## Pages

- `/` - Dashboard overview + top articles
- `/articles` - Browse all articles
- `/articles/[id]` - Article detail
- `/search` - Full-text search
- `/search` - Full-text and semantic search
- `/briefings` - Daily briefings
- `/clusters` - Event clustering view
- `/inbox` - Personal read/save/hide triage
- `/jarvis` - Natural-language query UI
- `/operations` - Queue, DLQ, pipeline and service overview
- `/projects` - Research project stream
- `/sources` - Source health and controls
- `/watchlist` - Entity watchlist and matches

## Components

- `ArticleCard` - Article preview with score badge
- `SearchBox` - Search input
- `LoadingSpinner` - Loading indicator
- `ErrorMessage` - Error display

## API Client

`src/lib/api.ts` wraps FastAPI endpoints:
- `api.getArticles(limit, offset)`
- `api.getSimilarArticles(id, limit)`
- `api.search(query, limit)`
- `api.semanticSearch(query, limit)`
- `api.getClusters(limit, offset)`
- `api.getDailyBriefing()`
- `api.jarvisQuery(query)`
- `api.getSources()`
- `api.getSourceHealth()`
- `api.getOpsSummary()`
- `api.getDeadQueues()`
- `api.getInbox()`
- `api.getWatchlist()`
- `api.getProjects()`
