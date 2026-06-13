"""
Worker cluster - consumes queue:cluster and groups semantically similar articles.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.db.models import Article, ArticleAI, ArticleCluster, Cluster
from app.storage.postgres import get_session, log_processing, mark_raw_item_status
from app.storage.redis_queue import dequeue, deserialize_payload, enqueue, enqueue_dead
from app.utils.logging import get_logger, setup_logging

log = get_logger("worker.cluster")

CLUSTER_SIMILARITY_THRESHOLD = float(os.environ.get("CLUSTER_SIMILARITY_THRESHOLD", "0.88"))
CLUSTER_WINDOW_HOURS = int(os.environ.get("CLUSTER_WINDOW_HOURS", "72"))
CLUSTER_MAX_RETRIES = int(os.environ.get("CLUSTER_MAX_RETRIES", "3"))
LOW_POWER_MODE = os.environ.get("LOW_POWER_MODE", "false").lower() in {"1", "true", "yes", "on"}
WORKER_RATE_LIMIT_MS = int(os.environ.get("CLUSTER_WORKER_RATE_LIMIT_MS", os.environ.get("WORKER_RATE_LIMIT_MS", "0")))


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
    if next_retry <= CLUSTER_MAX_RETRIES:
        enqueue("cluster", {"payload": payload, "retry_count": next_retry})
    else:
        enqueue_dead("cluster", payload, reason=error, retry_count=retry_count)


def _loop_pause() -> None:
    delay_ms = WORKER_RATE_LIMIT_MS
    if LOW_POWER_MODE and delay_ms == 0:
        delay_ms = 150
    if delay_ms > 0:
        time.sleep(delay_ms / 1000.0)


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _pick_best_cluster(session, article: Article, target_embedding: list[float]) -> tuple[int | None, float]:
    now = datetime.now(timezone.utc)
    if article.published_at:
        center = article.published_at
        if center.tzinfo is None:
            center = center.replace(tzinfo=timezone.utc)
    else:
        center = now

    window = timedelta(hours=CLUSTER_WINDOW_HOURS)
    start = center - window
    end = center + window

    distance_expr = ArticleAI.embedding.cosine_distance(target_embedding).label("distance")

    q = (
        select(Article.id, ArticleCluster.cluster_id, distance_expr)
        .join(ArticleAI, ArticleAI.article_id == Article.id)
        .outerjoin(ArticleCluster, ArticleCluster.article_id == Article.id)
        .where(Article.id != article.id)
        .where(ArticleAI.embedding.is_not(None))
        .where(Article.published_at.is_not(None))
        .where(Article.published_at >= start)
        .where(Article.published_at <= end)
        .order_by(distance_expr.asc())
        .limit(250)
    )

    rows = session.execute(q).all()
    best_cluster_id = None
    best_similarity = 0.0

    for _, cluster_id, distance in rows:
        similarity = 1.0 - _safe_float(distance, 1.0)
        if similarity < CLUSTER_SIMILARITY_THRESHOLD:
            continue
        if cluster_id is not None and similarity > best_similarity:
            best_cluster_id = int(cluster_id)
            best_similarity = similarity

    return best_cluster_id, best_similarity


def _upsert_cluster_link(session, article_id: int, cluster_id: int, similarity: float) -> bool:
    existing = session.get(ArticleCluster, (article_id, cluster_id))
    if existing:
        return False

    session.add(
        ArticleCluster(
            article_id=article_id,
            cluster_id=cluster_id,
            similarity_score=round(similarity, 3),
        )
    )
    session.flush()
    return True


def _refresh_cluster_metadata(session, cluster_id: int, article: Article, ai: ArticleAI, now: datetime) -> None:
    cluster = session.get(Cluster, cluster_id)
    if not cluster:
        return

    article_count = session.execute(
        select(func.count())
        .select_from(ArticleCluster)
        .where(ArticleCluster.cluster_id == cluster_id)
    ).scalar_one()

    cluster.article_count = int(article_count)
    cluster.last_seen_at = now

    score = _safe_float(ai.final_score, 0.0)
    current = _safe_float(cluster.importance_score, 0.0)
    if score >= current:
        cluster.importance_score = round(score, 3)
        if article.title:
            cluster.main_title = article.title
        if ai.summary_short:
            cluster.main_summary = ai.summary_short

    if not cluster.main_title and article.title:
        cluster.main_title = article.title
    if not cluster.main_summary and ai.summary_short:
        cluster.main_summary = ai.summary_short


def _process_article(article_id: int) -> None:
    with get_session() as session:
        now = datetime.now(timezone.utc)

        article = session.get(Article, article_id)
        if not article:
            log.warning("cluster_article_not_found", article_id=article_id)
            return

        ai = session.get(ArticleAI, article_id)
        if not ai:
            log.warning("cluster_missing_ai", article_id=article_id)
            log_processing(session, "article", article_id, "cluster", "skip", "missing article_ai")
            return

        if ai.embedding is None:
            log.warning("cluster_missing_embedding", article_id=article_id)
            log_processing(session, "article", article_id, "cluster", "skip", "missing embedding")
            return

        try:
            best_cluster_id, similarity = _pick_best_cluster(session, article, ai.embedding)
        except Exception as exc:
            log.error("cluster_similarity_error", article_id=article_id, error=str(exc))
            log_processing(session, "article", article_id, "cluster", "error", f"similarity error: {exc}")
            return

        if best_cluster_id is None:
            cluster = Cluster(
                main_title=article.title,
                main_summary=ai.summary_short,
                topic=ai.category,
                language=article.language,
                first_seen_at=article.published_at or now,
                last_seen_at=now,
                article_count=0,
                importance_score=round(_safe_float(ai.final_score, 0.0), 3),
            )
            session.add(cluster)
            session.flush()
            cluster_id = int(cluster.id)
            similarity = 1.0
            log.info("cluster_created", article_id=article_id, cluster_id=cluster_id)
        else:
            cluster_id = int(best_cluster_id)

        inserted = _upsert_cluster_link(session, article_id, cluster_id, similarity)
        if inserted:
            _refresh_cluster_metadata(session, cluster_id, article, ai, now)
            if article.raw_item_id:
                mark_raw_item_status(session, article.raw_item_id, "clustered")
            log_processing(
                session,
                "article",
                article_id,
                "cluster",
                "success",
                f"cluster={cluster_id} similarity={round(similarity, 3)}",
            )
            log.info("cluster_attached", article_id=article_id, cluster_id=cluster_id, similarity=round(similarity, 3))
        else:
            log_processing(session, "article", article_id, "cluster", "skip", f"already_linked cluster={cluster_id}")
            log.debug("cluster_already_linked", article_id=article_id, cluster_id=cluster_id)


def main() -> None:
    setup_logging("worker.cluster")
    log.info(
        "cluster_worker_start",
        similarity_threshold=CLUSTER_SIMILARITY_THRESHOLD,
        window_hours=CLUSTER_WINDOW_HOURS,
    )

    while True:
        raw = None
        try:
            raw = dequeue("cluster", timeout=5)
            if raw is None:
                continue
            payload, retry_count = _decode_retry_payload(raw)
            article_id = int(payload.strip())
            _process_article(article_id)
        except ValueError:
            log.warning("cluster_invalid_queue_payload", raw=raw)
        except Exception as exc:
            if raw:
                payload, retry_count = _decode_retry_payload(raw)
                _requeue_or_dead(payload, retry_count, str(exc))
            log.error("cluster_loop_error", error=str(exc))
        finally:
            _loop_pause()


if __name__ == "__main__":
    main()
