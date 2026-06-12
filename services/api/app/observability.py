from __future__ import annotations

import time

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

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


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
