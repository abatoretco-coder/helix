from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import init_db
from app.routes import articles, briefings, clusters, health, jarvis, search, sources


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
