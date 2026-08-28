"""
Worker extract — consumes queue:extract, calls the extractor chain,
stores raw HTML in MinIO, inserts articles in PostgreSQL,
pushes article_id to queue:ai.

Extractor chain (from architecture doc):
  1. RSS content (if full)
  2. morss (https://github.com/pictuga/morss)
  3. trafilatura (https://github.com/adbar/trafilatura)
  4. news-please (https://github.com/fhamborg/news-please)
  5. newspaper4k
  6. Playwright (if use_playwright=True in source config)
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from sqlalchemy import select

from app.db.models import RawItem, Article
from app.extractors.article import extract_article
from app.storage.postgres import get_session, mark_raw_item_status, log_processing
from app.storage.redis_queue import dequeue, deserialize_payload, enqueue, enqueue_dead, queue_size
from app.storage.minio import store_raw_html, store_raw_json
from app.policy.relevance import item_decision
from app.utils.hashing import hash_content
from app.utils.logging import get_logger, setup_logging

log = get_logger("worker.extract")

EXTRACT_MAX_RETRIES = int(os.environ.get("EXTRACT_MAX_RETRIES", "3"))
EXTRACT_RETRY_BACKOFF_SECONDS = int(os.environ.get("EXTRACT_RETRY_BACKOFF_SECONDS", "300"))
EXTRACT_RETRY_MAX_BACKOFF_SECONDS = int(os.environ.get("EXTRACT_RETRY_MAX_BACKOFF_SECONDS", "3600"))
EXTRACT_RETRY_SCAN_LIMIT = int(os.environ.get("EXTRACT_RETRY_SCAN_LIMIT", "25"))
EXTRACT_NEW_RECOVERY_BATCH_SIZE = int(os.environ.get("EXTRACT_NEW_RECOVERY_BATCH_SIZE", "25"))
LOW_POWER_MODE = os.environ.get("LOW_POWER_MODE", "false").lower() in {"1", "true", "yes", "on"}
WORKER_RATE_LIMIT_MS = int(os.environ.get("EXTRACT_WORKER_RATE_LIMIT_MS", os.environ.get("WORKER_RATE_LIMIT_MS", "0")))
AI_QUEUE_MAX_PENDING = max(1, int(os.environ.get("AI_QUEUE_MAX_PENDING", "50")))


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
    if next_retry <= EXTRACT_MAX_RETRIES:
        enqueue("extract", {"payload": payload, "retry_count": next_retry})
    else:
        enqueue_dead("extract", payload, reason=error, retry_count=retry_count)


def _loop_pause() -> None:
    delay_ms = WORKER_RATE_LIMIT_MS
    if LOW_POWER_MODE and delay_ms == 0:
        delay_ms = 150
    if delay_ms > 0:
        time.sleep(delay_ms / 1000.0)


def _retry_at(retry_count: int) -> datetime:
    delay = min(EXTRACT_RETRY_BACKOFF_SECONDS * (2 ** max(retry_count - 1, 0)), EXTRACT_RETRY_MAX_BACKOFF_SECONDS)
    return datetime.now(timezone.utc) + timedelta(seconds=delay)


def _enqueue_due_retries() -> int:
    now = datetime.now(timezone.utc)
    with get_session() as session:
        rows = (
            session.execute(
                select(RawItem)
                .where(RawItem.status == "retry_pending")
                .where(RawItem.next_retry_at.is_not(None))
                .where(RawItem.next_retry_at <= now)
                .order_by(RawItem.next_retry_at.asc())
                .limit(EXTRACT_RETRY_SCAN_LIMIT)
            )
            .scalars()
            .all()
        )
        for raw_item in rows:
            raw_item.status = "queued_for_extraction"
            raw_item.error_message = None
            enqueue("extract", {"payload": str(raw_item.id), "retry_count": int(raw_item.retry_count or 0)})
        if rows:
            log.info("extract_due_retries_enqueued", count=len(rows))
        return len(rows)


def _recover_committed_new_items() -> int:
    """Recover rows committed before a Redis hand-off was interrupted.

    This specifically repairs the former collect-before-commit race.  It only
    handles `new` records, applies the current admission policy again, and
    marks the row before enqueueing because the raw row is already committed.
    """
    with get_session() as session:
        rows = (
            session.execute(
                select(RawItem)
                .where(RawItem.status == "new")
                .order_by(RawItem.created_at.asc())
                .limit(EXTRACT_NEW_RECOVERY_BATCH_SIZE)
            )
            .scalars()
            .all()
        )
        accepted_ids: list[int] = []
        for raw_item in rows:
            decision = item_decision(raw_item.source, raw_item.title, raw_item.snippet, raw_item.published_at)
            if decision.accepted:
                raw_item.status = "queued_for_extraction"
                accepted_ids.append(int(raw_item.id))
            else:
                mark_raw_item_status(session, raw_item.id, "filtered_out", decision.reason)
        if accepted_ids:
            log.info("extract_new_recovery_claimed", count=len(accepted_ids))
    for raw_item_id in accepted_ids:
        enqueue("extract", str(raw_item_id))
    return len(accepted_ids)


def _compute_quality_score(article) -> float:
    """Quick quality heuristic — mirrors scoring_rules.yaml logic."""
    score = 0.0
    if article.title:
        score += 10
    if article.text_content and len(article.text_content) > 1000:
        score += 30
    elif article.text_content and len(article.text_content) > 200:
        score += 15
    if article.published_at:
        score += 10
    if article.author:
        score += 5
    if article.image_url:
        score += 5
    if article.word_count and article.word_count > 500:
        score += 20
    elif article.word_count and article.word_count > 100:
        score += 10
    if article.language:
        score += 10
    if article.description:
        score += 10
    return min(score, 100.0)


def _is_google_news_relay(url: str) -> bool:
    """Google News RSS links often resolve to consent/relay pages, not news."""
    parsed = urlparse(url)
    return parsed.netloc.endswith("news.google.com") and parsed.path.startswith("/rss/articles/")


def _process_item(raw_item_id: int) -> None:
    ai_article_id: int | None = None
    with get_session() as session:
        raw_item = session.get(RawItem, raw_item_id)
        if not raw_item:
            log.warning("raw_item_not_found", id=raw_item_id)
            return

        # Already processed?
        if raw_item.status in ("extracted", "ai_processed", "duplicate"):
            return

        admission = item_decision(raw_item.source, raw_item.title, raw_item.snippet, raw_item.published_at)
        if not admission.accepted:
            mark_raw_item_status(session, raw_item.id, "filtered_out", admission.reason)
            log_processing(session, "raw_item", raw_item.id, "extract", "skip", admission.reason)
            log.info("extract_filtered", raw_item_id=raw_item.id, reason=admission.reason)
            return

        t0 = time.monotonic()
        url  = raw_item.url
        strat = "article"
        if raw_item.source:
            strat = raw_item.source.extraction_strategy or "article"
        use_playwright = strat in ("playwright", "js", "browser")

        mark_raw_item_status(session, raw_item.id, "queued_for_extraction")

        # Never let a Google consent/redirect page become an apparent article.
        # The feed link is discovery metadata, not evidence.  A future decoder
        # may resolve it to the publisher URL; until then it is excluded rather
        # than being summarized as low-value pseudo-content.
        if _is_google_news_relay(url):
            mark_raw_item_status(session, raw_item.id, "filtered_out", "google_news_relay_unresolved")
            log_processing(session, "raw_item", raw_item.id, "extract", "skip", "google_news_relay_unresolved")
            log.info("extract_filtered", raw_item_id=raw_item.id, reason="google_news_relay_unresolved")
            return

        # ── Extract ─────────────────────────────────────────────────────────
        extracted = extract_article(
            url=url,
            raw_payload=raw_item.raw_payload or {},
            extraction_strategy=strat,
            use_playwright=use_playwright,
        )

        if not extracted or not extracted.text_content:
            raw_item.retry_count = int(raw_item.retry_count or 0) + 1
            current_retry = int(raw_item.retry_count)
            if current_retry <= EXTRACT_MAX_RETRIES:
                raw_item.next_retry_at = _retry_at(current_retry)
                mark_raw_item_status(session, raw_item.id, "retry_pending", "no content extracted")
                log_processing(
                    session,
                    "raw_item",
                    raw_item.id,
                    "extract",
                    "retry",
                    (
                        f"no content extracted; retry={current_retry}/{EXTRACT_MAX_RETRIES} "
                        f"next_retry_at={raw_item.next_retry_at.isoformat()}"
                    ),
                )
                log.warning("extract_empty_retry_scheduled", url=url, retry=current_retry, next_retry_at=raw_item.next_retry_at.isoformat())
            else:
                raw_item.next_retry_at = None
                mark_raw_item_status(session, raw_item.id, "failed", "no content extracted")
                enqueue_dead("extract", str(raw_item.id), reason="no content extracted", retry_count=current_retry)
                log_processing(
                    session,
                    "raw_item",
                    raw_item.id,
                    "extract",
                    "error",
                    f"no content extracted; sent to dead-letter after {current_retry} retries",
                )
                log.warning("extract_empty_dead_letter", url=url, retry=current_retry)
            return

        # Check again with the extracted title and description before storing
        # expensive raw payloads or placing work in the AI queue.
        admission = item_decision(
            raw_item.source,
            extracted.title or raw_item.title,
            # The RSS teaser can look editorial while the article itself
            # discloses sponsorship or affiliate links.  Check the extracted
            # body before we retain it or send it to Ollama.
            f"{extracted.description or raw_item.snippet or ''} {extracted.text_content or ''}",
            raw_item.published_at,
        )
        if not admission.accepted:
            mark_raw_item_status(session, raw_item.id, "filtered_out", admission.reason)
            log_processing(session, "raw_item", raw_item.id, "extract", "skip", admission.reason)
            log.info("extract_filtered", raw_item_id=raw_item.id, reason=admission.reason)
            return

        # ── Deduplication by content hash ────────────────────────────────────
        content_hash = hash_content(extracted.text_content)
        existing = session.execute(
            select(Article.id).where(Article.content_hash == content_hash)
        ).scalar_one_or_none()

        if existing:
            raw_item.next_retry_at = None
            mark_raw_item_status(session, raw_item.id, "duplicate")
            log_processing(session, "raw_item", raw_item.id, "extract", "skip", "duplicate content")
            log.debug("extract_duplicate", url=url)
            return

        # ── Store raw HTML in MinIO ───────────────────────────────────────────
        html_path = None
        json_path = None
        source_slug = (
            raw_item.source.name.lower().replace(" ", "_")[:30]
            if raw_item.source else "unknown"
        )

        if extracted.raw_html:
            try:
                html_path = store_raw_html(raw_item.id, source_slug, extracted.raw_html)
            except Exception as exc:
                log.warning("minio_html_store_failed", url=url, error=str(exc))

        try:
            json_path = store_raw_json(raw_item.id, source_slug, raw_item.raw_payload or {})
        except Exception as exc:
            log.warning("minio_json_store_failed", url=url, error=str(exc))

        # ── Insert article ───────────────────────────────────────────────────
        published_at = None
        if extracted.published_at:
            try:
                from dateutil import parser as date_parser
                published_at = date_parser.parse(str(extracted.published_at))
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
            except Exception:
                pass
        if not published_at:
            published_at = raw_item.published_at

        quality = _compute_quality_score(extracted)

        article = Article(
            raw_item_id=raw_item.id,
            source_id=raw_item.source_id,
            url=url,
            normalized_url=raw_item.normalized_url,
            canonical_url=raw_item.canonical_url,
            title=extracted.title or raw_item.title,
            description=extracted.description,
            text_content=extracted.text_content,
            author=extracted.author,
            language=extracted.language,
            published_at=published_at,
            discovered_at=raw_item.discovered_at,
            image_url=extracted.image_url,
            word_count=extracted.word_count,
            content_hash=content_hash,
            quality_score=quality,
            extractor_used=extracted.extractor_used,
            raw_html_path=html_path,
            raw_json_path=json_path,
            extraction_status="success",
        )
        session.add(article)
        session.flush()
        article_id = article.id

        raw_item.next_retry_at = None
        mark_raw_item_status(session, raw_item.id, "extracted")
        if queue_size("ai") < AI_QUEUE_MAX_PENDING:
            # Do not publish an AI job before this transaction is committed.
            # Otherwise the AI worker can consume it immediately and report
            # article_not_found, permanently losing the enrichment request.
            ai_article_id = article_id
        else:
            mark_raw_item_status(session, raw_item.id, "ai_pending", "waiting_for_ai_capacity")
            log.info("extract_ai_deferred", article_id=article_id, queue_size=queue_size("ai"))

        duration_ms = int((time.monotonic() - t0) * 1000)
        log_processing(session, "raw_item", raw_item.id, "extract", "success",
                       f"article {article_id} via {extracted.extractor_used}",
                       duration_ms=duration_ms)
        log.info("extracted_ok", url=url, article_id=article_id,
                 extractor=extracted.extractor_used, words=extracted.word_count, ms=duration_ms)

    if ai_article_id is not None:
        enqueue("ai", str(ai_article_id))


def main():
    setup_logging("worker.extract")
    log.info("extract_worker_start")

    while True:
        raw = None
        try:
            raw = dequeue("extract", timeout=5)
            if raw is None:
                _enqueue_due_retries()
                _recover_committed_new_items()
                continue
            payload, retry_count = _decode_retry_payload(raw)
            raw_item_id = int(payload.strip())
            _process_item(raw_item_id)
        except ValueError:
            log.warning("invalid_queue_payload", raw=raw)
        except Exception as exc:
            if raw:
                payload, retry_count = _decode_retry_payload(raw)
                _requeue_or_dead(payload, retry_count, str(exc))
            log.error("extract_loop_error", error=str(exc))
        finally:
            _loop_pause()


if __name__ == "__main__":
    main()
