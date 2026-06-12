"""RSS / Atom collector using feedparser."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import feedparser

from app.utils.logging import get_logger

log = get_logger("collector.rss")


def _parse_date(entry: dict) -> Optional[datetime]:
    for field in ("published", "updated", "created"):
        val = entry.get(f"{field}_parsed") or entry.get(field)
        if val is None:
            continue
        if hasattr(val, "tm_year"):
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                continue
        if isinstance(val, str):
            try:
                return parsedate_to_datetime(val).replace(tzinfo=timezone.utc)
            except Exception:
                continue
    return None


def _extract_text(entry: dict) -> Optional[str]:
    """Try content first, then summary."""
    for field in ("content", "summary_detail", "summary"):
        val = entry.get(field)
        if not val:
            continue
        if isinstance(val, list) and val:
            return val[0].get("value", "")
        if isinstance(val, dict):
            return val.get("value", "")
        if isinstance(val, str):
            return val
    return None


def collect_rss(source: dict) -> list[dict]:
    """
    Parse an RSS/Atom feed.
    Returns list of raw item dicts.
    """
    url = source.get("url")
    if not url:
        log.warning("rss_no_url", source_name=source.get("name"))
        return []

    log.info("rss_fetch", url=url)
    feed = feedparser.parse(url, request_headers={"User-Agent": "NewsNAS/1.0 (+https://github.com)"})

    if feed.get("bozo"):
        log.warning("rss_parse_warning", url=url, exc=str(feed.get("bozo_exception", "")))

    items = []
    for entry in feed.entries:
        link = entry.get("link") or entry.get("id")
        if not link:
            continue

        items.append({
            "url": link,
            "title": entry.get("title", "").strip(),
            "snippet": (_extract_text(entry) or "")[:500],
            "published_at": _parse_date(entry),
            "raw_payload": {
                "feed_title": feed.feed.get("title"),
                "entry_id": entry.get("id"),
                "author": entry.get("author"),
                "tags": [t.get("term") for t in entry.get("tags", [])],
            },
        })

    log.info("rss_done", url=url, count=len(items))
    return items
