import json
import os

import redis.asyncio as redis_async

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")


def _client() -> redis_async.Redis:
    return redis_async.from_url(REDIS_URL, decode_responses=True)


async def enqueue(queue_name: str, payload) -> None:
    value = payload
    if isinstance(payload, (dict, list)):
        value = json.dumps(payload)
    client = _client()
    try:
        await client.rpush(f"queue:{queue_name}", str(value))
    finally:
        await client.aclose()


async def queue_size(queue_name: str) -> int:
    client = _client()
    try:
        return int(await client.llen(f"queue:{queue_name}"))
    finally:
        await client.aclose()


async def dead_queue_size(queue_name: str) -> int:
    client = _client()
    try:
        return int(await client.llen(f"queue:{queue_name}:dead"))
    finally:
        await client.aclose()


async def dead_queue_items(queue_name: str, limit: int = 100) -> list[str]:
    client = _client()
    try:
        return [str(item) for item in await client.lrange(f"queue:{queue_name}:dead", -max(limit, 1), -1)]
    finally:
        await client.aclose()


async def retry_dead_queue(queue_name: str, limit: int | None = None) -> int:
    client = _client()
    dead_key = f"queue:{queue_name}:dead"
    try:
        items = await client.lrange(dead_key, 0, -1 if limit is None else max(limit - 1, 0))
        if not items:
            return 0
        for raw in items:
            original = raw
            try:
                payload = json.loads(raw)
                original = payload.get("original_payload", raw)
            except Exception:
                pass
            if isinstance(original, (dict, list)):
                original = json.dumps(original)
            await client.rpush(f"queue:{queue_name}", str(original))

        trim_from = len(items) if limit is None or limit >= len(items) else limit
        await client.ltrim(dead_key, trim_from, -1)
        return len(items)
    finally:
        await client.aclose()


async def purge_dead_queue(queue_name: str) -> int:
    client = _client()
    dead_key = f"queue:{queue_name}:dead"
    try:
        count = int(await client.llen(dead_key))
        await client.delete(dead_key)
        return count
    finally:
        await client.aclose()
