from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import init_db
from app.routes import articles, briefings, clusters, health, jarvis, metrics, search, sources
from app.security import require_api_token


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="News NAS API",
    version="0.1.0",
    description="Personal news intelligence platform API.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # local network only — tighten if exposed externally
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(sources.router, prefix="/sources", tags=["sources"])
app.include_router(articles.router, prefix="/articles", tags=["articles"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(clusters.router, prefix="/clusters", tags=["clusters"])
app.include_router(briefings.router, prefix="/briefings", tags=["briefings"])
app.include_router(jarvis.router, prefix="/jarvis", tags=["jarvis"])
app.include_router(metrics.router, tags=["operations"])

# Versioned contract for Jarvis and other clients.
app.include_router(health.router, prefix="/v1")
app.include_router(sources.router, prefix="/v1/sources", tags=["sources-v1"], dependencies=[Depends(require_api_token)])
app.include_router(articles.router, prefix="/v1/articles", tags=["articles-v1"], dependencies=[Depends(require_api_token)])
app.include_router(search.router, prefix="/v1/search", tags=["search-v1"], dependencies=[Depends(require_api_token)])
app.include_router(clusters.router, prefix="/v1/clusters", tags=["clusters-v1"], dependencies=[Depends(require_api_token)])
app.include_router(briefings.router, prefix="/v1/briefings", tags=["briefings-v1"], dependencies=[Depends(require_api_token)])
app.include_router(jarvis.router, prefix="/v1/jarvis", tags=["jarvis-v1"], dependencies=[Depends(require_api_token)])
app.include_router(metrics.router, prefix="/v1", tags=["operations-v1"], dependencies=[Depends(require_api_token)])
