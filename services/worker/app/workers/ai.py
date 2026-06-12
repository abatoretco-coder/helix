"""
Worker AI — consumes queue:ai, runs the full AI pipeline per article,
saves article_ai, indexes in Meilisearch, pushes to queue:cluster.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.models import Article, ArticleAI
from app.ai.pipeline import (
    summarize_short, summarize_long,
    classify_article, extract_entities,
    generate_embedding, compute_scores,
)
from app.storage.postgres import get_session, mark_raw_item_status, log_processing
from app.storage.redis_queue import dequeue, enqueue
from app.storage.search import index_article
from app.utils.logging import get_logger, setup_logging

log = get_logger("worker.ai")

LLM_MODEL = __import__("os").environ.get("LLM_MODEL", "mistral")


def _process_article(article_id: int) -> None:
    with get_session() as session:
        article = session.get(Article, article_id)
        if not article:
            log.warning("article_not_found", id=article_id)
            return

        # Skip if already processed
        existing_ai = session.get(ArticleAI, article_id)
        if existing_ai and existing_ai.final_score is not None:
            log.debug("ai_already_processed", article_id=article_id)
            return

        t0 = time.monotonic()
        title = article.title or ""
        text  = article.text_content or ""

        if not text and not title:
            log.warning("ai_skip_no_content", article_id=article_id)
            return

        log.info("ai_start", article_id=article_id, title=title[:60])

        # 1. Summarize
        short_summary = summarize_short(title, text)
        long_summary  = summarize_long(title, text)

        # 2. Classify
        category = classify_article(title, text)

        # 3. Extract entities
        entities = extract_entities(title, text)

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
        )

        # 6. Save article_ai (upsert)
        ai_data = {
            "article_id": article_id,
            "summary_short": short_summary,
            "summary_long": long_summary,
            "category": category,
            "topics": [category],
            "entities": entities,
            "model_name": LLM_MODEL,
            "processed_at": datetime.now(timezone.utc),
            **scores,
        }
        if embedding:
            from pgvector.sqlalchemy import Vector
            ai_data["embedding"] = embedding

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
        try:
            raw = dequeue("ai", timeout=5)
            if raw is None:
                continue
            article_id = int(raw.strip())
            _process_article(article_id)
        except ValueError:
            log.warning("invalid_queue_payload", raw=raw)
        except Exception as exc:
            log.error("ai_loop_error", error=str(exc))


if __name__ == "__main__":
    main()
