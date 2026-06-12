"""
Worker collect — reads sources.yaml/DB, calls the right collector,
inserts raw_items, pushes to Redis queue:extract.
"""
from __future__ import annotations

import os
import time
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

import yaml
from sqlalchemy import select

from app.collectors.rss import collect_rss
from app.collectors.google_news import collect_google_news
from app.collectors.reddit import collect_reddit
from app.collectors.hackernews import collect_hackernews
from app.collectors.github import collect_github_trending
from app.collectors.youtube import collect_youtube
from app.storage.postgres import (
    get_session, upsert_raw_item,
    mark_source_success, mark_source_error, log_processing,
)
from app.storage.redis_queue import enqueue
from app.utils.urls import normalize_url
from app.utils.logging import get_logger, setup_logging
from app.db.models import Source

log = get_logger("worker.collect")

SOURCES_PATH = os.environ.get("SOURCES_PATH", "/app/config/sources.yaml")

_COLLECTOR_MAP = {
    "rss":             collect_rss,
    "atom":            collect_rss,
    "google_news_rss": collect_google_news,
    "reddit":          collect_reddit,
    "hackernews":      collect_hackernews,
    "github_trending": collect_github_trending,
    "youtube_channel": collect_youtube,
}


def _normalize_reddit_subreddit(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    v = value.strip()
    # First, try extracting from canonical Reddit URL/path.
    m = re.search(r"/r/([^/?#\s]+)", v, flags=re.IGNORECASE)
    if m:
        v = m.group(1)
    else:
        # Strip common labels like "Reddit - xxx" or "Reddit — xxx".
        v = re.sub(r"^\s*reddit\s*[:\-|\u2013\u2014]+\s*", "", v, flags=re.IGNORECASE)
        if "/" in v:
            v = v.split("/", 1)[0]
        # Keep last token for labels like "Tech - LocalLLaMA".
        parts = re.split(r"[\-|\u2013\u2014]", v)
        if len(parts) > 1:
            tail = parts[-1].strip()
            if tail:
                v = tail

    v = re.sub(r"\s+", "", v)
    v = v.lstrip("r/")
    return v or None


def _load_sources_yaml() -> list[dict]:
    """Load sources from YAML file (used on first run before DB is seeded)."""
    path = SOURCES_PATH
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return [s for s in data.get("sources", []) if s.get("enabled", True)]


def _sync_sources_to_db(session, yaml_sources: list[dict]) -> None:
    """Insert YAML sources into DB if they don't exist yet."""
    from app.db.models import Source
    for s in yaml_sources:
        url = s.get("url") or s.get("query") or s.get("subreddit") or s.get("hn_type") or ""
        existing = session.execute(
            select(Source).where(Source.name == s["name"])
        ).scalar_one_or_none()
        if existing:
            continue
        src = Source(
            name=s["name"],
            source_type=s["type"],
            url=s.get("url"),
            query=(
                s.get("query")
                or (s.get("subreddit") if s.get("type") == "reddit" else None)
                or (s.get("hn_type") if s.get("type") == "hackernews" else None)
                or (s.get("topic") if s.get("type") == "github_trending" else None)
            ),
            country=s.get("country"),
            language=s.get("language", "en"),
            category=s.get("category", "general"),
            priority=s.get("priority", 3),
            refresh_minutes=s.get("refresh_minutes", 60),
            extraction_strategy=s.get("extraction_strategy", "article"),
            enabled=s.get("enabled", True),
        )
        session.add(src)
    session.flush()


def _get_due_sources(session) -> list[Source]:
    """Return sources whose next check time has passed."""
    sources = session.execute(
        select(Source).where(Source.enabled == True)
    ).scalars().all()

    due = []
    now = datetime.now(timezone.utc)
    for src in sources:
        if src.last_checked_at is None:
            due.append(src)
            continue
        last = src.last_checked_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        next_check = last + timedelta(minutes=src.refresh_minutes)
        if now >= next_check:
            due.append(src)

    # Sort by priority
    due.sort(key=lambda s: s.priority)
    return due


def _run_once() -> int:
    """One full collection cycle. Returns number of new items queued."""
    total_new = 0

    with get_session() as session:
        # Seed DB from YAML on first run
        yaml_sources = _load_sources_yaml()
        if yaml_sources:
            _sync_sources_to_db(session, yaml_sources)

        due_sources = _get_due_sources(session)
        log.info("collect_cycle_start", due=len(due_sources))

        for source in due_sources:
            collector = _COLLECTOR_MAP.get(source.source_type)
            if not collector:
                log.warning("no_collector", source_type=source.source_type, source=source.name)
                continue

            t0 = time.monotonic()
            try:
                # Build config dict for collector
                source_dict = {
                    "name": source.name,
                    "type": source.source_type,
                    "url": source.url,
                    "query": source.query,
                    "language": source.language,
                    "country": source.country,
                    "subreddit": (
                        _normalize_reddit_subreddit(source.query)
                        or _normalize_reddit_subreddit(source.url)
                        or _normalize_reddit_subreddit(source.name)
                    ) if source.source_type == "reddit" else None,
                    "hn_type": source.query if source.source_type == "hackernews" else "topstories",
                    "topic": source.query if source.source_type == "github_trending" else None,
                    "channel_id": source.url if source.source_type == "youtube_channel" else None,
                }

                items = collector(source_dict)
                new_count = 0

                for item in items:
                    raw_url = item.get("url", "")
                    if not raw_url:
                        continue
                    norm_url = normalize_url(raw_url)
                    new_id = upsert_raw_item(
                        session,
                        source_id=source.id,
                        url=raw_url,
                        normalized_url=norm_url,
                        title=item.get("title"),
                        snippet=item.get("snippet"),
                        published_at=item.get("published_at"),
                        raw_payload=item.get("raw_payload", {}),
                    )
                    if new_id is not None:
                        enqueue("extract", str(new_id))
                        new_count += 1

                duration_ms = int((time.monotonic() - t0) * 1000)
                mark_source_success(session, source.id)
                log_processing(session, "source", source.id, "collect", "success",
                                f"{new_count} new items", duration_ms=duration_ms)
                log.info("source_collected", source=source.name, new=new_count, ms=duration_ms)
                total_new += new_count

            except Exception as exc:
                mark_source_error(session, source.id, str(exc))
                log.error("source_collect_error", source=source.name, error=str(exc))

    return total_new


def main():
    setup_logging("worker.collect")
    log.info("collect_worker_start")

    while True:
        try:
            new_items = _run_once()
            log.info("collect_cycle_done", new_items=new_items)
        except Exception as exc:
            log.error("collect_cycle_error", error=str(exc))

        # Sleep between cycles (60s default, shorter if items were found)
        sleep_s = 30 if new_items > 0 else 60
        time.sleep(sleep_s)


if __name__ == "__main__":
    main()
