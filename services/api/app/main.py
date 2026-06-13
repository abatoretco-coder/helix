from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import init_db
from app.observability import PrometheusMiddleware, router as observability_router
from app.routes import (
    alerts,
    articles,
    briefings,
    capabilities,
    clusters,
    contract,
    health,
    home_assistant,
    inbox,
    jarvis,
    metrics,
    projects,
    queues,
    search,
    sources,
    user_state,
    watchlist,
)
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
app.add_middleware(PrometheusMiddleware)

app.include_router(health.router)
app.include_router(observability_router)
app.include_router(sources.router, prefix="/sources", tags=["sources"])
app.include_router(articles.router, prefix="/articles", tags=["articles"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(clusters.router, prefix="/clusters", tags=["clusters"])
app.include_router(briefings.router, prefix="/briefings", tags=["briefings"])
app.include_router(jarvis.router, prefix="/jarvis", tags=["jarvis"])
app.include_router(metrics.router, tags=["operations"])
app.include_router(queues.router, prefix="/queues", tags=["queues"])
app.include_router(capabilities.router, prefix="/capabilities", tags=["capabilities"])
app.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(inbox.router, prefix="/inbox", tags=["inbox"])
app.include_router(home_assistant.router, prefix="/home-assistant", tags=["home-assistant"])
app.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
app.include_router(user_state.router, prefix="/user-state", tags=["user-state"])
app.include_router(contract.router, prefix="/contract", tags=["contract"])

# Versioned contract for Jarvis and other clients.
app.include_router(health.router, prefix="/v1")
app.include_router(sources.router, prefix="/v1/sources", tags=["sources-v1"], dependencies=[Depends(require_api_token)])
app.include_router(articles.router, prefix="/v1/articles", tags=["articles-v1"], dependencies=[Depends(require_api_token)])
app.include_router(search.router, prefix="/v1/search", tags=["search-v1"], dependencies=[Depends(require_api_token)])
app.include_router(clusters.router, prefix="/v1/clusters", tags=["clusters-v1"], dependencies=[Depends(require_api_token)])
app.include_router(briefings.router, prefix="/v1/briefings", tags=["briefings-v1"], dependencies=[Depends(require_api_token)])
app.include_router(jarvis.router, prefix="/v1/jarvis", tags=["jarvis-v1"], dependencies=[Depends(require_api_token)])
app.include_router(metrics.router, prefix="/v1", tags=["operations-v1"], dependencies=[Depends(require_api_token)])
app.include_router(queues.router, prefix="/v1/queues", tags=["queues-v1"], dependencies=[Depends(require_api_token)])
app.include_router(queues.admin_router, prefix="/v1/queues", tags=["queues-v1-admin"], dependencies=[Depends(require_api_token)])
app.include_router(capabilities.router, prefix="/v1/capabilities", tags=["capabilities-v1"], dependencies=[Depends(require_api_token)])
app.include_router(watchlist.router, prefix="/v1/watchlist", tags=["watchlist-v1"], dependencies=[Depends(require_api_token)])
app.include_router(projects.router, prefix="/v1/projects", tags=["projects-v1"], dependencies=[Depends(require_api_token)])
app.include_router(inbox.router, prefix="/v1/inbox", tags=["inbox-v1"], dependencies=[Depends(require_api_token)])
app.include_router(home_assistant.router, prefix="/v1/home-assistant", tags=["home-assistant-v1"], dependencies=[Depends(require_api_token)])
app.include_router(alerts.router, prefix="/v1/alerts", tags=["alerts-v1"], dependencies=[Depends(require_api_token)])
app.include_router(user_state.router, prefix="/v1/user-state", tags=["user-state-v1"], dependencies=[Depends(require_api_token)])
app.include_router(contract.router, prefix="/v1/contract", tags=["contract-v1"], dependencies=[Depends(require_api_token)])
