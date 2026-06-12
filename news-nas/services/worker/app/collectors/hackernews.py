"""Hacker News collector using the Firebase API."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import requests

from app.utils.logging import get_logger

log = get_logger("collector.hackernews")

_BASE = "https://hacker-news.firebaseio.com/v0"
_TYPES = {
    "topstories": f"{_BASE}/topstories.json",
    "beststories": f"{_BASE}/beststories.json",
    "newstories": f"{_BASE}/newstories.json",
    "askstories": f"{_BASE}/askstories.json",
    "showstories": f"{_BASE}/showstories.json",
}


def _fetch_item(item_id: int) -> Optional[dict]:
    try:
        r = requests.get(f"{_BASE}/item/{item_id}.json", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("hn_item_fetch_error", item_id=item_id, error=str(e))
        return None


def collect_hackernews(source: dict, max_items: int = 50) -> list[dict]:
    hn_type = source.get("hn_type", "topstories")
    endpoint = _TYPES.get(hn_type, _TYPES["topstories"])

    log.info("hn_fetch", hn_type=hn_type)
    try:
        r = requests.get(endpoint, timeout=10)
        r.raise_for_status()
        ids = r.json()[:max_items]
    except Exception as e:
        log.error("hn_list_fetch_error", error=str(e))
        return []

    items = []
    for item_id in ids:
        data = _fetch_item(item_id)
        if not data or data.get("type") not in ("story", "job"):
            continue
        url = data.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
        items.append({
            "url": url,
            "title": data.get("title", ""),
            "snippet": data.get("text", "")[:500] if data.get("text") else "",
            "published_at": datetime.fromtimestamp(data.get("time", 0), tz=timezone.utc),
            "raw_payload": {
                "hn_id": item_id,
                "score": data.get("score"),
                "descendants": data.get("descendants"),
                "author": data.get("by"),
                "hn_url": f"https://news.ycombinator.com/item?id={item_id}",
            },
        })

    log.info("hn_done", count=len(items))
    return items
