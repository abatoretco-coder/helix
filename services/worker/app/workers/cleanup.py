"""
Worker cleanup - runs periodic retention tasks for old logs and stale raw items.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update

from app.db.models import Article, ProcessingLog, RawItem, RetentionJob
from app.storage.minio import delete_objects_older_than
from app.storage.postgres import get_session, log_processing
from app.storage.search import delete_article
from app.policy.relevance import article_decision
from app.utils.logging import get_logger, setup_logging

log = get_logger("worker.cleanup")

CLEANUP_INTERVAL_SECONDS = int(os.environ.get("CLEANUP_INTERVAL_SECONDS", "3600"))
PROCESSING_LOG_RETENTION_DAYS = int(os.environ.get("PROCESSING_LOG_RETENTION_DAYS", "30"))
RAW_ITEM_RETENTION_DAYS = int(os.environ.get("RAW_ITEM_RETENTION_DAYS", "14"))
MINIO_RETENTION_ENABLED = os.environ.get("MINIO_RETENTION_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
RAW_HTML_RETENTION_DAYS = int(os.environ.get("RAW_HTML_RETENTION_DAYS", "90"))
RAW_JSON_RETENTION_DAYS = int(os.environ.get("RAW_JSON_RETENTION_DAYS", "365"))
ARTICLE_ARCHIVE_ENABLED = os.environ.get("ARTICLE_ARCHIVE_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
ARTICLE_ARCHIVE_DAYS = int(os.environ.get("ARTICLE_ARCHIVE_DAYS", "30"))
AD_FILTER_RETROACTIVE_ENABLED = os.environ.get("AD_FILTER_RETROACTIVE_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


def _run_cleanup() -> dict[str, int]:
    now = datetime.now(timezone.utc)
    log_cutoff = now - timedelta(days=PROCESSING_LOG_RETENTION_DAYS)
    raw_cutoff = now - timedelta(days=RAW_ITEM_RETENTION_DAYS)
    html_cutoff = now - timedelta(days=RAW_HTML_RETENTION_DAYS)
    json_cutoff = now - timedelta(days=RAW_JSON_RETENTION_DAYS)
    article_cutoff = now - timedelta(days=ARTICLE_ARCHIVE_DAYS)

    deleted_logs = 0
    deleted_raw = 0
    deleted_raw_html = 0
    deleted_raw_json = 0
    archived_articles = 0
    archived_article_ids: list[int] = []
    policy_articles = 0
    policy_article_ids: list[int] = []
    policy_reason_counts: dict[str, int] = {}
    minio_error = None
    retention_job_id: int | None = None

    with get_session() as session:
        job = RetentionJob(
            job_type="periodic_cleanup",
            status="running",
            cutoff_days=min(PROCESSING_LOG_RETENTION_DAYS, RAW_ITEM_RETENTION_DAYS, RAW_HTML_RETENTION_DAYS, RAW_JSON_RETENTION_DAYS),
            started_at=now,
            details={
                "processing_log_cutoff": log_cutoff.isoformat(),
                "raw_item_cutoff": raw_cutoff.isoformat(),
                "raw_html_cutoff": html_cutoff.isoformat(),
                "raw_json_cutoff": json_cutoff.isoformat(),
                "article_archive_cutoff": article_cutoff.isoformat(),
                "article_archive_enabled": ARTICLE_ARCHIVE_ENABLED,
                "ad_filter_retroactive_enabled": AD_FILTER_RETROACTIVE_ENABLED,
                "minio_retention_enabled": MINIO_RETENTION_ENABLED,
            },
        )
        session.add(job)
        session.flush()
        retention_job_id = int(job.id)

        deleted_logs = session.execute(
            delete(ProcessingLog).where(ProcessingLog.created_at < log_cutoff)
        ).rowcount or 0

        deleted_raw = session.execute(
            delete(RawItem)
            .where(RawItem.created_at < raw_cutoff)
            .where(RawItem.status.in_(["duplicate", "failed"]))
        ).rowcount or 0

        if ARTICLE_ARCHIVE_ENABLED:
            archived_article_ids = [
                int(article_id)
                for article_id in session.execute(
                    select(Article.id)
                    .where(Article.archived_at.is_(None))
                    .where(Article.published_at.is_not(None))
                    .where(Article.published_at < article_cutoff)
                ).scalars().all()
            ]
            archived_articles = session.execute(
                update(Article)
                .where(Article.archived_at.is_(None))
                .where(Article.published_at.is_not(None))
                .where(Article.published_at < article_cutoff)
                .values(archived_at=now)
            ).rowcount or 0

        # This is a safe, reversible active-view cleanup. A policy decision is
        # an admission rule, not merely a collector preference: legacy rows
        # rejected today must not remain visible, searchable or AI-backfillable.
        # Records stay in PostgreSQL for audit; no LLM is called here.
        if AD_FILTER_RETROACTIVE_ENABLED:
            active_articles = session.execute(
                select(Article).where(Article.archived_at.is_(None))
            ).scalars().all()
            for article in active_articles:
                decision = article_decision(article)
                if not decision.accepted:
                    policy_article_ids.append(int(article.id))
                    policy_reason_counts[decision.reason] = policy_reason_counts.get(decision.reason, 0) + 1
            if policy_article_ids:
                policy_articles = session.execute(
                    update(Article)
                    .where(Article.id.in_(policy_article_ids))
                    .where(Article.archived_at.is_(None))
                    .values(archived_at=now)
                ).rowcount or 0
                archived_article_ids.extend(policy_article_ids)

        job.deleted_count = int(deleted_logs + deleted_raw + deleted_raw_html + deleted_raw_json)
        job.status = "warning" if minio_error else "success"
        job.details = {
            **(job.details or {}),
            "deleted_logs": int(deleted_logs),
            "deleted_raw_items": int(deleted_raw),
            "deleted_raw_html_objects": int(deleted_raw_html),
            "deleted_raw_json_objects": int(deleted_raw_json),
            "archived_articles": int(archived_articles),
            "policy_articles_archived": int(policy_articles),
            "policy_archive_reasons": policy_reason_counts,
            "minio_error": minio_error,
        }
        job.finished_at = datetime.now(timezone.utc)

        log_processing(
            session,
            "retention",
            int(job.id),
            "cleanup",
            job.status,
            (
                f"deleted_logs={deleted_logs} deleted_raw={deleted_raw} "
                f"deleted_raw_html={deleted_raw_html} deleted_raw_json={deleted_raw_json}"
                f" archived_articles={archived_articles} policy_articles_archived={policy_articles}"
            ),
        )

    # Object-store retention is intentionally after database admission cleanup.
    # A slow MinIO listing must never prevent policy-rejected articles from
    # leaving the active news product.
    if MINIO_RETENTION_ENABLED:
        try:
            deleted_raw_html = delete_objects_older_than("raw_html/", html_cutoff)
            deleted_raw_json = delete_objects_older_than("raw_json/", json_cutoff)
        except Exception as exc:
            minio_error = str(exc)
            log.warning("cleanup_minio_retention_failed", error=minio_error)
            if retention_job_id is not None:
                with get_session() as session:
                    job = session.get(RetentionJob, retention_job_id)
                    if job:
                        job.status = "warning"
                        job.details = {**(job.details or {}), "minio_error": minio_error}
                        job.finished_at = datetime.now(timezone.utc)

    # Search is an active view: archived records stay in PostgreSQL but must
    # disappear from Meilisearch so they cannot leak back into the dashboard.
    for article_id in set(archived_article_ids):
        try:
            delete_article(article_id)
        except Exception as exc:
            log.warning("cleanup_archive_search_remove_failed", article_id=article_id, error=str(exc))

    return {
        "deleted_logs": int(deleted_logs),
        "deleted_raw": int(deleted_raw),
        "deleted_raw_html": int(deleted_raw_html),
        "deleted_raw_json": int(deleted_raw_json),
        "archived_articles": int(archived_articles),
        "policy_articles_archived": int(policy_articles),
    }


def main() -> None:
    setup_logging("worker.cleanup")
    log.info(
        "cleanup_worker_start",
        interval_seconds=CLEANUP_INTERVAL_SECONDS,
        processing_log_retention_days=PROCESSING_LOG_RETENTION_DAYS,
        raw_item_retention_days=RAW_ITEM_RETENTION_DAYS,
        raw_html_retention_days=RAW_HTML_RETENTION_DAYS,
        raw_json_retention_days=RAW_JSON_RETENTION_DAYS,
        article_archive_enabled=ARTICLE_ARCHIVE_ENABLED,
        article_archive_days=ARTICLE_ARCHIVE_DAYS,
        ad_filter_retroactive_enabled=AD_FILTER_RETROACTIVE_ENABLED,
        minio_retention_enabled=MINIO_RETENTION_ENABLED,
    )

    while True:
        try:
            result = _run_cleanup()
            log.info("cleanup_cycle_done", **result)
        except Exception as exc:
            log.error("cleanup_cycle_error", error=str(exc))
        time.sleep(CLEANUP_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
