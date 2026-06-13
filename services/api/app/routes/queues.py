import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.queue import dead_queue_items, dead_queue_size, purge_dead_queue, retry_dead_queue

router = APIRouter()
admin_router = APIRouter()

ALLOWED_QUEUES = {"extract", "ai", "cluster", "briefing"}


def _assert_queue(queue_name: str) -> None:
    if queue_name not in ALLOWED_QUEUES:
        raise HTTPException(status_code=404, detail="Unknown queue")


def _parse_payload(raw: str):
    try:
        return json.loads(raw)
    except Exception:
        return raw


@router.get("/dead")
async def list_dead_queues():
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "queues": {queue_name: await dead_queue_size(queue_name) for queue_name in sorted(ALLOWED_QUEUES)},
    }


@router.get("/dead/{queue_name}")
async def list_dead_queue_items(queue_name: str, limit: int = Query(default=50, ge=1, le=500)):
    _assert_queue(queue_name)
    rows = await dead_queue_items(queue_name, limit=limit)
    return {
        "queue": queue_name,
        "count": len(rows),
        "items": [_parse_payload(raw) for raw in rows],
    }


@admin_router.post("/dead/{queue_name}/retry")
async def retry_dead_queue_items(queue_name: str, limit: int = Query(default=50, ge=1, le=1000)):
    _assert_queue(queue_name)
    moved = await retry_dead_queue(queue_name, limit=limit)
    return {
        "queue": queue_name,
        "retried": moved,
    }


@admin_router.post("/dead/{queue_name}/purge")
async def purge_dead_queue_items(queue_name: str):
    _assert_queue(queue_name)
    purged = await purge_dead_queue(queue_name)
    return {
        "queue": queue_name,
        "purged": purged,
    }
