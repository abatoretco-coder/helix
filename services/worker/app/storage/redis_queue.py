"""Redis queue helpers."""
import json
import os
from datetime import datetime, timezone

import redis

_redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
_client: redis.Redis = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(_redis_url, decode_responses=True)
    return _client


def enqueue(queue_name: str, payload) -> None:
    r = get_redis()
    if isinstance(payload, (dict, list)):
        payload = json.dumps(payload)
    r.rpush(f"queue:{queue_name}", str(payload))


def deserialize_payload(raw: str):
    try:
        return json.loads(raw)
    except Exception:
        return raw


def enqueue_dead(queue_name: str, payload, reason: str | None = None, retry_count: int | None = None) -> None:
    dead_payload = {
        "original_payload": payload,
        "queue": queue_name,
        "error": reason,
        "failed_at": datetime.now(timezone.utc).isoformat(),
        "retry_count": retry_count,
    }
    enqueue(f"{queue_name}:dead", dead_payload)


def move_to_dead_letter(queue_name: str, payload: str, error: str) -> None:
    enqueue_dead(queue_name, payload, reason=error)


def dequeue(queue_name: str, timeout: int = 5) -> str | None:
    """Blocking pop with timeout. Returns raw string or None."""
    r = get_redis()
    result = r.blpop(f"queue:{queue_name}", timeout=timeout)
    if result:
        _, value = result
        return value
    return None


def queue_size(queue_name: str) -> int:
    return get_redis().llen(f"queue:{queue_name}")


def dead_queue_size(queue_name: str) -> int:
    return get_redis().llen(f"queue:{queue_name}:dead")


def dead_queue_items(queue_name: str, limit: int = 100) -> list[str]:
    return get_redis().lrange(f"queue:{queue_name}:dead", 0, max(limit - 1, 0))


def retry_dead_queue(queue_name: str, limit: int | None = None) -> int:
    r = get_redis()
    dead_key = f"queue:{queue_name}:dead"
    items = r.lrange(dead_key, 0, -1 if limit is None else max(limit - 1, 0))
    if not items:
        return 0
    for raw in items:
        try:
            payload = json.loads(raw)
            original = payload.get("original_payload", raw)
        except Exception:
            original = raw
        enqueue(queue_name, original)
    if limit is None or limit >= len(items):
        r.ltrim(dead_key, len(items), -1)
    else:
        r.ltrim(dead_key, limit, -1)
    return len(items)


def purge_dead_queue(queue_name: str) -> int:
    r = get_redis()
    dead_key = f"queue:{queue_name}:dead"
    count = r.llen(dead_key)
    r.delete(dead_key)
    return int(count)
