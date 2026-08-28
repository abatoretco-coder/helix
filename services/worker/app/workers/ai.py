"""
Worker AI — consumes queue:ai, runs the full AI pipeline per article,
saves article_ai, indexes in Meilisearch, pushes to queue:cluster.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import or_, select

from app.db.models import Article, ArticleAI, RawItem
from app.ai.pipeline import (
    normalize_article,
    generate_embedding, compute_scores,
)
from app.storage.postgres import get_session, mark_raw_item_status, log_processing
from app.storage.redis_queue import dequeue, deserialize_payload, enqueue, enqueue_dead, queue_size
from app.storage.search import delete_article, index_article
from app.policy.relevance import article_decision
from app.utils.logging import get_logger, setup_logging

log = get_logger("worker.ai")

LLM_MODEL = os.environ.get("OPENAI_MODEL", os.environ.get("LLM_MODEL", "gpt-4.1-mini"))
BACKGROUND_AI_ENABLED = os.environ.get("BACKGROUND_AI_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
AI_MAX_RETRIES = int(os.environ.get("AI_MAX_RETRIES", "3"))
LOW_POWER_MODE = os.environ.get("LOW_POWER_MODE", "false").lower() in {"1", "true", "yes", "on"}
WORKER_RATE_LIMIT_MS = int(os.environ.get("AI_WORKER_RATE_LIMIT_MS", os.environ.get("WORKER_RATE_LIMIT_MS", "0")))
AI_BACKFILL_ENABLED = os.environ.get("AI_BACKFILL_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
AI_BACKFILL_REFRESH_EXISTING = os.environ.get("AI_BACKFILL_REFRESH_EXISTING", "false").strip().lower() in {"1", "true", "yes", "on"}
AI_BACKFILL_BATCH_SIZE = max(1, min(int(os.environ.get("AI_BACKFILL_BATCH_SIZE", "20")), 100))
AI_QUEUE_MAX_PENDING = max(1, int(os.environ.get("AI_QUEUE_MAX_PENDING", "50")))
AI_PENDING_REFILL_BATCH_SIZE = max(1, min(int(os.environ.get("AI_PENDING_REFILL_BATCH_SIZE", "10")), 50))
AI_PENDING_REFILL_ENABLED = os.environ.get("AI_PENDING_REFILL_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


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
    if next_retry <= AI_MAX_RETRIES:
        enqueue("ai", {"payload": payload, "retry_count": next_retry})
    else:
        enqueue_dead("ai", payload, reason=error, retry_count=retry_count)


def _loop_pause() -> None:
    delay_ms = WORKER_RATE_LIMIT_MS
    if LOW_POWER_MODE and delay_ms == 0:
        delay_ms = 150
    if delay_ms > 0:
        time.sleep(delay_ms / 1000.0)


def _fallback_category(article) -> str:
    """Cheap, deterministic fallback; never make a second LLM call on failure."""
    blob = " ".join(
        str(value or "")
        for value in (getattr(article, "title", None), getattr(article, "description", None), getattr(article, "text_content", None))
    ).lower()
    if any(term in blob for term in ("cybersecurity", "cyberattaque", "ransomware", "malware", "botnet", "vulnerability", "vulnerabilit", "exploit", "piratage")):
        return "Cybersecurity"
    if any(term in blob for term in ("artificial intelligence", "intelligence artificielle", "large language model", " llm", "openai", "anthropic", "mistral", "gemini", "ollama")):
        return "AI"
    if any(term in blob for term in ("supply chain", "logistique", "freight", "warehouse", "entrepot")):
        return "Supply Chain"
    if any(term in blob for term in ("regulation", "reglementation", "ai act", "directive", "commission europeenne")):
        return "European Regulation"
    category = (article.source.category if article.source else "") or ""
    mapping = {
        "ai": "AI", "tech": "SaaS", "supply_chain": "Supply Chain",
        "pharma": "Pharma Logistics", "climate": "Climate",
        "cybersecurity": "Cybersecurity", "startups": "Startups",
        "regulation": "European Regulation", "geopolitics": "Geopolitics",
        "finance": "Finance", "science": "Other",
    }
    return mapping.get(category.strip().lower(), "Other")


def _empty_entities() -> dict[str, list[str]]:
    return {
        "people": [], "companies": [], "countries": [], "cities": [],
        "products": [], "technologies": [], "regulations": [],
    }


def _enqueue_backfill_batch() -> int:
    """Schedule a small, non-duplicating batch of articles without AI data.

    This keeps the Redis queue bounded while progressively bringing the existing
    catalogue to the same Ollama-backed database format as new articles.
    """
    if not AI_BACKFILL_ENABLED:
        return 0
    with get_session() as session:
        statement = (
            select(Article.id)
            .outerjoin(ArticleAI, ArticleAI.article_id == Article.id)
            .where(Article.archived_at.is_(None))
            .where(
                or_(
                    ArticleAI.article_id.is_(None),
                    ArticleAI.model_name.is_distinct_from(LLM_MODEL) if AI_BACKFILL_REFRESH_EXISTING else ArticleAI.article_id.is_(None),
                )
            )
            .order_by(Article.published_at.desc().nullslast(), Article.id.desc())
            .limit(AI_BACKFILL_BATCH_SIZE)
        )
        article_ids = [int(article_id) for article_id in session.execute(statement).scalars().all()]
    for article_id in article_ids:
        enqueue("ai", str(article_id))
    if article_ids:
        log.info("ai_backfill_enqueued", count=len(article_ids), first_article_id=article_ids[0])
    return len(article_ids)


def _enqueue_pending_ai_batch() -> int:
    """Move only a small deferred batch into Redis once capacity is available."""
    if not AI_PENDING_REFILL_ENABLED:
        return 0
    capacity = AI_QUEUE_MAX_PENDING - queue_size("ai")
    if capacity <= 0:
        return 0
    limit = min(capacity, AI_PENDING_REFILL_BATCH_SIZE)
    with get_session() as session:
        rows = (
            session.execute(
                select(Article)
                .join(RawItem, RawItem.id == Article.raw_item_id)
                .where(Article.archived_at.is_(None))
                .where(RawItem.status == "ai_pending")
                .order_by(Article.published_at.desc().nullslast(), Article.id.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
        article_ids = [int(article.id) for article in rows]
        for article in rows:
            mark_raw_item_status(session, article.raw_item_id, "queued_for_ai")
    for article_id in article_ids:
        enqueue("ai", str(article_id))
    if article_ids:
        log.info("ai_pending_refilled", count=len(article_ids))
    return len(article_ids)


def _process_article(article_id: int) -> None:
    with get_session() as session:
        article = session.get(Article, article_id)
        if not article:
            log.warning("article_not_found", id=article_id)
            return
        if article.archived_at is not None:
            log.info("ai_skip_archived", article_id=article_id)
            return

        admission = article_decision(article)
        if not admission.accepted:
            # A policy decision is an active-view removal, not merely a skipped
            # enrichment task.  Otherwise a previously stored article can leak
            # through search, a briefing or Jarvis even though it was rejected.
            article.archived_at = datetime.now(timezone.utc)
            if article.raw_item_id:
                mark_raw_item_status(session, article.raw_item_id, "filtered_out", admission.reason)
            log_processing(session, "article", article_id, "ai", "skip", admission.reason)
            session.commit()
            try:
                delete_article(article_id)
            except Exception as exc:
                log.warning("ai_filtered_search_remove_failed", article_id=article_id, error=str(exc))
            log.info("ai_filtered", article_id=article_id, reason=admission.reason)
            return

        # Skip if already processed
        existing_ai = session.get(ArticleAI, article_id)
        if existing_ai and existing_ai.final_score is not None and (
            not AI_BACKFILL_REFRESH_EXISTING or existing_ai.model_name == LLM_MODEL
        ):
            log.debug("ai_already_processed", article_id=article_id)
            return

        t0 = time.monotonic()
        title = article.title or ""
        text  = article.text_content or ""

        if not text and not title:
            log.warning("ai_skip_no_content", article_id=article_id)
            return

        log.info("ai_start", article_id=article_id, title=title[:60])

        # 1. Normalize once with the local model.  This is the canonical
        # database shape for every collected article and avoids four separate
        # generation calls for the same source text.
        normalized = normalize_article(title, text)
        short_summary = normalized.get("summary_short") or ""
        long_summary = normalized.get("summary_long") or ""

        if not short_summary:
            short_summary = (article.description or title or "No summary available")[:800]
        if not long_summary:
            long_summary = short_summary

        # 2. Use the normalized taxonomy; retain conservative fallbacks if a
        # local model is temporarily unavailable or returns invalid JSON.
        category = normalized.get("category") or _fallback_category(article)
        if str(category).strip().lower() in {"", "other"}:
            category = _fallback_category(article)

        # 3. Entity lists and sentiment are stored with the same record.
        entities = normalized.get("entities") or _empty_entities()
        if not isinstance(entities, dict):
            entities = {}

        # 4. Embedding on title + short summary (compact, fast)
        embed_text = f"{title}\n{short_summary}"
        embedding  = generate_embedding(embed_text)

        # 5. Compute scores
        source_name = article.source.name if article.source else ""
        scores = compute_scores(
            article=article,
            category=category,
            quality_score=float(article.quality_score or 0),
            published_at=article.published_at,
            source_name=source_name,
            entities=entities,
        )

        # 6. Save article_ai (upsert)
        ai_data = {
            "article_id": article_id,
            "summary_short": short_summary,
            "summary_long": long_summary,
            "category": category,
            "topics": normalized.get("topics") or [category],
            "entities": entities,
            "sentiment": normalized.get("sentiment") or "neutral",
            "model_name": LLM_MODEL if BACKGROUND_AI_ENABLED else "metadata-only",
            "processed_at": datetime.now(timezone.utc),
            **scores,
        }
        if embedding:
            ai_data["embedding"] = embedding
        else:
            log.warning("ai_partial_success", article_id=article_id, reason="missing_embedding")

        stmt = pg_insert(ArticleAI).values(**ai_data).on_conflict_do_update(
            index_elements=["article_id"],
            set_={k: v for k, v in ai_data.items() if k != "article_id"},
        )
        session.execute(stmt)
        session.flush()

        # 7. Index in Meilisearch
        meili_doc = {
            "id": article_id,
            "title": title,
            "url": article.url,
            "source": source_name,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "language": article.language or "en",
            "category": category,
            "summary_short": short_summary,
            "summary_long": long_summary,
            "entities": entities,
            "final_score": scores["final_score"],
            "quality_score": float(article.quality_score or 0),
        }
        try:
            index_article(meili_doc)
        except Exception as exc:
            log.warning("meili_index_error", article_id=article_id, error=str(exc))

        # 8. Update raw_item status
        if article.raw_item_id:
            mark_raw_item_status(session, article.raw_item_id, "ai_processed")

        duration_ms = int((time.monotonic() - t0) * 1000)
        log_processing(session, "article", article_id, "ai", "success",
                       f"cat={category} score={scores['final_score']}", duration_ms=duration_ms)

        # Commit DB state before queueing clustering to avoid race conditions.
        session.commit()

        # 9. Push to clustering queue
        enqueue("cluster", str(article_id))
        log.info("ai_done", article_id=article_id, category=category,
                 score=scores["final_score"], ms=duration_ms)


def main():
    setup_logging("worker.ai")
    log.info("ai_worker_start")

    while True:
        raw = None
        try:
            raw = dequeue("ai", timeout=5)
            if raw is None:
                _enqueue_pending_ai_batch()
                _enqueue_backfill_batch()
                continue
            payload, retry_count = _decode_retry_payload(raw)
            article_id = int(payload.strip())
            _process_article(article_id)
        except ValueError:
            log.warning("invalid_queue_payload", raw=raw)
        except Exception as exc:
            if raw:
                payload, retry_count = _decode_retry_payload(raw)
                _requeue_or_dead(payload, retry_count, str(exc))
            log.error("ai_loop_error", error=str(exc))
        finally:
            _loop_pause()


if __name__ == "__main__":
    main()
