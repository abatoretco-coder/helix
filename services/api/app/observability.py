from __future__ import annotations

import time

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from sqlalchemy import func, select, text
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.models import Article, ArticleAI, ProcessingLog, RawItem, Source
from app.db.session import AsyncSessionLocal

REQUEST_COUNT = Counter(
    "helix_api_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "helix_api_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)
REQUEST_IN_PROGRESS = Gauge(
    "helix_api_http_requests_in_progress",
    "Number of in-progress HTTP requests",
)

SOURCES_TOTAL = Gauge("helix_sources_total", "Total configured sources")
SOURCES_ENABLED = Gauge("helix_sources_enabled_total", "Enabled sources")
SOURCES_WITH_ERRORS = Gauge("helix_sources_with_errors_total", "Sources with non-zero errors")
RAW_ITEMS_TOTAL = Gauge("helix_raw_items_total", "Raw items discovered")
ARTICLES_TOTAL = Gauge("helix_articles_total", "Extracted articles total")
ARTICLE_AI_TOTAL = Gauge("helix_article_ai_total", "AI-enriched articles total")
PROCESSING_ERRORS_24H = Gauge("helix_processing_errors_24h_total", "Processing errors in last 24 hours")


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method
        path = request.url.path
        start = time.perf_counter()

        REQUEST_IN_PROGRESS.inc()
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.perf_counter() - start
            REQUEST_COUNT.labels(method=method, path=path, status_code=str(status_code)).inc()
            REQUEST_LATENCY.labels(method=method, path=path).observe(duration)
            REQUEST_IN_PROGRESS.dec()

        return response


router = APIRouter()


async def _refresh_pipeline_gauges() -> None:
    async with AsyncSessionLocal() as db:
        SOURCES_TOTAL.set((await db.execute(select(func.count()).select_from(Source))).scalar_one())
        SOURCES_ENABLED.set(
            (await db.execute(select(func.count()).select_from(Source).where(Source.enabled == True))).scalar_one()
        )
        SOURCES_WITH_ERRORS.set(
            (await db.execute(select(func.count()).select_from(Source).where(Source.error_count > 0))).scalar_one()
        )
        RAW_ITEMS_TOTAL.set((await db.execute(select(func.count()).select_from(RawItem))).scalar_one())
        ARTICLES_TOTAL.set((await db.execute(select(func.count()).select_from(Article))).scalar_one())
        ARTICLE_AI_TOTAL.set((await db.execute(select(func.count()).select_from(ArticleAI))).scalar_one())
        PROCESSING_ERRORS_24H.set(
            (
                await db.execute(
                    select(func.count())
                    .select_from(ProcessingLog)
                    .where(ProcessingLog.status == "error")
                    .where(ProcessingLog.created_at >= text("now() - interval '24 hours'"))
                )
            ).scalar_one()
        )


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    try:
        await _refresh_pipeline_gauges()
    except Exception:
        # Keep metrics endpoint available even if DB gauge refresh fails.
        pass
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
