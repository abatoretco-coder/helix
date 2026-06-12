"""Redis queue helpers."""
import os
import json
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
