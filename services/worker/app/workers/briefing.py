"""
Worker briefing - consumes queue:briefing and generates markdown briefings.
"""
from __future__ import annotations

import os
import time
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import desc, func, select
from sqlalchemy.orm import selectinload

from app.db.models import Article, ArticleAI, Briefing
from app.storage.postgres import get_session, log_processing
from app.storage.redis_queue import dequeue, deserialize_payload, enqueue, enqueue_dead
from app.utils.logging import get_logger, setup_logging

log = get_logger("worker.briefing")

TOP_ARTICLES_LIMIT = 25
BRIEFING_ITEMS_LIMIT = 10
DAILY_BRIEFING_ENABLED = os.environ.get("DAILY_BRIEFING_ENABLED", os.environ.get("SCHEDULER_ENABLE_DAILY_BRIEFING", "true")).lower() in {
    "1",
    "true",
    "yes",
    "on",
}
DAILY_BRIEFING_TIMEZONE = os.environ.get("DAILY_BRIEFING_TIMEZONE", "Europe/Paris")
DAILY_BRIEFING_HOUR = int(os.environ.get("DAILY_BRIEFING_HOUR", "7"))
DAILY_BRIEFING_MINUTE = int(os.environ.get("DAILY_BRIEFING_MINUTE", "30"))
DAILY_BRIEFING_CATEGORY = os.environ.get("DAILY_BRIEFING_CATEGORY", os.environ.get("SCHEDULER_BRIEFING_CATEGORY", "all"))
BRIEFING_TICK_SECONDS = int(os.environ.get("BRIEFING_TICK_SECONDS", os.environ.get("SCHEDULER_TICK_SECONDS", "30")))
BRIEFING_MAX_RETRIES = int(os.environ.get("BRIEFING_MAX_RETRIES", "3"))

# The daily scheduler is intentionally embedded in worker_briefing to avoid one more container.


def _decode_retry_payload(raw: str) -> tuple[str, int]:
    parsed = deserialize_payload(raw)
    if isinstance(parsed, dict):
        payload = parsed.get("payload") or parsed.get("original_payload")
        retry_count = int(parsed.get("retry_count", 0) or 0)
        if payload is None:
            payload = raw
        return str(payload), retry_count
    return raw, 0


def _requeue_or_dead(payload: str, retry_count: int, error: str) -> None:
    next_retry = retry_count + 1
    if next_retry <= BRIEFING_MAX_RETRIES:
        enqueue("briefing", {"payload": payload, "retry_count": next_retry})
    else:
        enqueue_dead("briefing", payload, reason=error, retry_count=retry_count)


def _local_now() -> datetime:
    return datetime.now(ZoneInfo(DAILY_BRIEFING_TIMEZONE))


def _parse_payload(payload: str) -> tuple[str, date, str]:
    parts = payload.strip().split(":", 2)
    if len(parts) not in (2, 3):
        raise ValueError(f"invalid payload format: {payload}")

    if len(parts) == 2:
        period, category = parts
        raw_date = ""
    else:
        period, raw_date, category = parts

    raw_date = raw_date.strip()
    if raw_date:
        try:
            period_date = date.fromisoformat(raw_date)
        except ValueError:
            period_date = datetime.now(timezone.utc).date()
            log.warning("briefing_invalid_date_fallback", raw_date=raw_date, fallback=period_date.isoformat())
    else:
        period_date = datetime.now(timezone.utc).date()

    return period.strip(), period_date, (category.strip() or "all")


def _select_articles(session, period_date: date, category: str) -> list[Article]:
    article_date = func.date(
        func.coalesce(
            Article.published_at,
            Article.discovered_at,
            Article.extracted_at,
        )
    )

    q = (
        select(Article)
        .join(ArticleAI, ArticleAI.article_id == Article.id)
        .options(selectinload(Article.ai), selectinload(Article.source), selectinload(Article.clusters))
        .where(article_date == period_date)
        .order_by(desc(ArticleAI.final_score), desc(Article.published_at))
        .limit(TOP_ARTICLES_LIMIT)
    )

    if category != "all":
        q = q.where(ArticleAI.category == category)

    return list(session.execute(q).scalars().all())


def _select_for_briefing(articles: list[Article]) -> tuple[list[Article], list[int]]:
    selected: list[Article] = []
    selected_ids: set[int] = set()
    used_clusters: set[int] = set()

    # First pass: keep one representative per cluster.
    for article in articles:
        if len(selected) >= BRIEFING_ITEMS_LIMIT:
            break

        cluster_ids = [int(link.cluster_id) for link in (article.clusters or [])]
        if not cluster_ids:
            continue

        if any(cluster_id in used_clusters for cluster_id in cluster_ids):
            continue

        selected.append(article)
        selected_ids.add(int(article.id))
        used_clusters.update(cluster_ids)

    # Second pass: fill with top-scored remaining articles.
    for article in articles:
        if len(selected) >= BRIEFING_ITEMS_LIMIT:
            break
        if int(article.id) in selected_ids:
            continue
        selected.append(article)
        selected_ids.add(int(article.id))

    return selected, sorted(used_clusters)


def _build_markdown(period: str, period_date: date, category: str, articles: list[Article]) -> tuple[str, list[int]]:
    article_ids: list[int] = [int(a.id) for a in articles]
    header = f"# Helix {period.title()} Briefing"
    meta = [
        f"Date: {period_date.isoformat()}",
        f"Category: {category}",
        "",
        "## Top News",
    ]

    lines: list[str] = [header, "", *meta, ""]
    for idx, article in enumerate(articles, start=1):
        ai = article.ai
        source_name = article.source.name if article.source else "Unknown"
        summary = ai.summary_short if ai and ai.summary_short else (article.description or "No summary available")
        score = float(ai.final_score) if ai and ai.final_score is not None else 0.0

        lines.extend(
            [
                f"### {idx}. {article.title or 'Untitled'}",
                f"- Source: {source_name}",
                f"- URL: {article.url}",
                f"- Score: {score:.3f}",
                f"- Summary: {summary}",
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n", article_ids


def _upsert_briefing(session, period: str, period_date: date, category: str, content: str, article_ids: list[int], cluster_ids: list[int]) -> int:
    existing = session.execute(
        select(Briefing).where(
            Briefing.period == period,
            func.date(Briefing.period_date) == period_date,
            Briefing.category == category,
        )
    ).scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if existing:
        existing.content = content
        existing.article_ids = article_ids
        existing.cluster_ids = cluster_ids
        existing.generated_at = now
        session.flush()
        return int(existing.id)

    briefing = Briefing(
        period=period,
        period_date=period_date,
        category=category,
        content=content,
        article_ids=article_ids,
        cluster_ids=cluster_ids,
        generated_at=now,
    )
    session.add(briefing)
    session.flush()
    return int(briefing.id)


def _process_payload(payload: str) -> None:
    period, period_date, category = _parse_payload(payload)

    if period != "daily":
        log.warning("briefing_period_not_supported", period=period, payload=payload)
        return

    with get_session() as session:
        articles = _select_articles(session, period_date, category)
        chosen_articles, chosen_cluster_ids = _select_for_briefing(articles)
        content, chosen_article_ids = _build_markdown(period, period_date, category, chosen_articles)

        briefing_id = _upsert_briefing(
            session,
            period=period,
            period_date=period_date,
            category=category,
            content=content,
            article_ids=chosen_article_ids,
            cluster_ids=chosen_cluster_ids,
        )

        log_processing(
            session,
            "briefing",
            briefing_id,
            "briefing",
            "success",
            f"period={period} date={period_date.isoformat()} category={category} articles={len(chosen_article_ids)}",
        )

        log.info(
            "briefing_generated",
            briefing_id=briefing_id,
            period=period,
            date=period_date.isoformat(),
            category=category,
            article_count=len(chosen_article_ids),
            cluster_count=len(chosen_cluster_ids),
        )


def _maybe_enqueue_daily_briefing(last_enqueued_date: date | None) -> date | None:
    if not DAILY_BRIEFING_ENABLED:
        return last_enqueued_date

    now_local = _local_now()
    should_enqueue = (
        now_local.hour == DAILY_BRIEFING_HOUR
        and now_local.minute == DAILY_BRIEFING_MINUTE
        and last_enqueued_date != now_local.date()
    )
    if not should_enqueue:
        return last_enqueued_date

    payload = f"daily:{now_local.date().isoformat()}:{DAILY_BRIEFING_CATEGORY}"
    enqueue("briefing", payload)
    log.info("briefing_scheduler_enqueued", payload=payload, timezone=DAILY_BRIEFING_TIMEZONE)
    return now_local.date()


def main() -> None:
    setup_logging("worker.briefing")
    log.info(
        "briefing_worker_start",
        daily_briefing_enabled=DAILY_BRIEFING_ENABLED,
        briefing_timezone=DAILY_BRIEFING_TIMEZONE,
        briefing_hour=DAILY_BRIEFING_HOUR,
        briefing_minute=DAILY_BRIEFING_MINUTE,
        briefing_category=DAILY_BRIEFING_CATEGORY,
        tick_seconds=BRIEFING_TICK_SECONDS,
    )

    last_daily_briefing_date = None

    while True:
        raw = None
        try:
            raw = dequeue("briefing", timeout=5)
            if raw is None:
                last_daily_briefing_date = _maybe_enqueue_daily_briefing(last_daily_briefing_date)
                time.sleep(BRIEFING_TICK_SECONDS)
                continue
            payload, retry_count = _decode_retry_payload(raw)
            _process_payload(payload)
        except ValueError as exc:
            log.warning("briefing_invalid_queue_payload", raw=raw, error=str(exc))
        except Exception as exc:
            if raw:
                payload, retry_count = _decode_retry_payload(raw)
                _requeue_or_dead(payload, retry_count, str(exc))
            log.error("briefing_loop_error", error=str(exc), raw=raw)


if __name__ == "__main__":
    main()
