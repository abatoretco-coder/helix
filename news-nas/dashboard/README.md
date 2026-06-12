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
- `/search` - Full-text search
- `/briefings` - Daily briefings
- `/clusters` - Event clustering view

## Components

- `ArticleCard` - Article preview with score badge
- `SearchBox` - Search input
- `LoadingSpinner` - Loading indicator
- `ErrorMessage` - Error display

## API Client

`src/lib/api.ts` wraps FastAPI endpoints:
- `api.getArticles(limit, offset)`
- `api.search(query, limit)`
- `api.getClusters(limit, offset)`
- `api.getDailyBriefing()`
- `api.jarvisQuery(query)`
- `api.getSources()`
