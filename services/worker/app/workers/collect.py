"""
Worker collect — reads sources.yaml/DB, calls the right collector,
inserts raw_items, pushes to Redis queue:extract.
"""
from __future__ import annotations

import os
import time
import re
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Optional

import yaml
from sqlalchemy import select, update

from app.collectors.rss import collect_rss
from app.collectors.google_news import collect_google_news
from app.collectors.reddit import collect_reddit
from app.collectors.hackernews import collect_hackernews
from app.collectors.github import collect_github_trending
from app.collectors.youtube import collect_youtube
from app.collectors.structured_api import (
    collect_cisa_kev, collect_eurostat, collect_github_advisories,
    collect_github_releases, collect_openalex, collect_datagouv_dataset,
)
from app.storage.postgres import (
    get_session, upsert_raw_item,
    mark_source_success, mark_source_error, log_processing,
)
from app.storage.redis_queue import enqueue
from app.policy.relevance import item_decision, source_decision
from app.utils.urls import normalize_url
from app.utils.logging import get_logger, setup_logging
from app.db.models import RawItem, Source

log = get_logger("worker.collect")

SOURCES_PATH = os.environ.get("SOURCES_PATH", "/app/config/sources.yaml")
COLLECT_ACTIVE_SLEEP_SECONDS = int(os.environ.get("COLLECT_ACTIVE_SLEEP_SECONDS", "30"))
COLLECT_IDLE_SLEEP_SECONDS = int(os.environ.get("COLLECT_IDLE_SLEEP_SECONDS", "60"))
COLLECT_MAX_DUE_SOURCES = int(os.environ.get("COLLECT_MAX_DUE_SOURCES", "0"))

_COLLECTOR_MAP = {
    "rss":             collect_rss,
    "atom":            collect_rss,
    "google_news_rss": collect_google_news,
    "reddit":          collect_reddit,
    "hackernews":      collect_hackernews,
    "github_trending": collect_github_trending,
    "youtube_channel": collect_youtube,
    "cisa_kev":       collect_cisa_kev,
    "github_advisories": collect_github_advisories,
    "github_releases": collect_github_releases,
    "openalex":       collect_openalex,
    "eurostat":       collect_eurostat,
    "datagouv_dataset": collect_datagouv_dataset,
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
    for s in yaml_sources:
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
        if not source_decision(src).accepted:
            continue
        if src.last_checked_at is None:
            due.append(src)
            continue
        last = src.last_checked_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        next_check = last + timedelta(minutes=src.refresh_minutes)
        if now >= next_check:
            due.append(src)

    def due_rank(source: Source) -> tuple[int, float]:
        last = source.last_checked_at
        if last is None:
            return int(source.priority or 3), float("-inf")
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return int(source.priority or 3), last.timestamp()

    # Priority first, then oldest checked source to avoid starving lower-volume feeds.
    due.sort(key=due_rank)
    if COLLECT_MAX_DUE_SOURCES > 0 and len(due) > COLLECT_MAX_DUE_SOURCES:
        log.info("collect_due_limited", due=len(due), selected=COLLECT_MAX_DUE_SOURCES)
        due = due[:COLLECT_MAX_DUE_SOURCES]
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
                duplicate_count = 0
                filtered_count = 0
                filtered_reasons: Counter[str] = Counter()
                new_item_ids: list[int] = []

                for item in items:
                    raw_url = item.get("url", "")
                    if not raw_url:
                        continue
                    decision = item_decision(
                        source,
                        item.get("title"),
                        item.get("snippet"),
                        item.get("published_at"),
                    )
                    if not decision.accepted:
                        filtered_count += 1
                        filtered_reasons[decision.reason or "policy_rejected"] += 1
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
                        # Never publish a queue message for an uncommitted row.
                        # The extract worker can otherwise consume it before this
                        # source transaction is visible and permanently lose it.
                        new_item_ids.append(int(new_id))
                        new_count += 1
                    else:
                        duplicate_count += 1

                duration_ms = int((time.monotonic() - t0) * 1000)
                mark_source_success(session, source.id)
                log_processing(session, "source", source.id, "collect", "success",
                                f"fetched={len(items)} new={new_count} duplicates={duplicate_count} "
                                f"filtered={filtered_count} reasons={dict(filtered_reasons)}",
                                payload={
                                    "fetched": len(items),
                                    "new": new_count,
                                    "duplicates": duplicate_count,
                                    "filtered": filtered_count,
                                    "filtered_reasons": dict(filtered_reasons),
                                },
                                duration_ms=duration_ms)
                # Persist progress source-by-source to avoid long-cycle data loss on restart.
                session.commit()
                for raw_item_id in new_item_ids:
                    enqueue("extract", str(raw_item_id))
                if new_item_ids:
                    # A committed `new` row is recoverable if Redis is briefly
                    # unavailable; after successful enqueue, mark its intended
                    # next stage for operational visibility.
                    session.execute(
                        update(RawItem)
                        .where(RawItem.id.in_(new_item_ids), RawItem.status == "new")
                        .values(status="queued_for_extraction")
                    )
                    session.commit()
                log.info(
                    "source_collected",
                    source=source.name,
                    fetched=len(items),
                    new=new_count,
                    duplicates=duplicate_count,
                    filtered=filtered_count,
                    filtered_reasons=dict(filtered_reasons),
                    ms=duration_ms,
                )
                total_new += new_count

            except Exception as exc:
                session.rollback()
                mark_source_error(session, source.id, str(exc))
                session.commit()
                log.error("source_collect_error", source=source.name, error=str(exc))

    return total_new


def main():
    setup_logging("worker.collect")
    log.info(
        "collect_worker_start",
        active_sleep_seconds=COLLECT_ACTIVE_SLEEP_SECONDS,
        idle_sleep_seconds=COLLECT_IDLE_SLEEP_SECONDS,
        max_due_sources=COLLECT_MAX_DUE_SOURCES,
    )
    new_items = 0

    while True:
        try:
            new_items = _run_once()
            log.info("collect_cycle_done", new_items=new_items)
        except Exception as exc:
            log.error("collect_cycle_error", error=str(exc))

        sleep_s = COLLECT_ACTIVE_SLEEP_SECONDS if new_items > 0 else COLLECT_IDLE_SLEEP_SECONDS
        time.sleep(sleep_s)


if __name__ == "__main__":
    main()
