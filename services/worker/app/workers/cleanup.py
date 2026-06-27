"""
Worker cleanup - runs periodic retention tasks for old logs and stale raw items.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from app.db.models import ProcessingLog, RawItem, RetentionJob
from app.storage.minio import delete_objects_older_than
from app.storage.postgres import get_session, log_processing
from app.utils.logging import get_logger, setup_logging

log = get_logger("worker.cleanup")

CLEANUP_INTERVAL_SECONDS = int(os.environ.get("CLEANUP_INTERVAL_SECONDS", "3600"))
PROCESSING_LOG_RETENTION_DAYS = int(os.environ.get("PROCESSING_LOG_RETENTION_DAYS", "30"))
RAW_ITEM_RETENTION_DAYS = int(os.environ.get("RAW_ITEM_RETENTION_DAYS", "14"))
MINIO_RETENTION_ENABLED = os.environ.get("MINIO_RETENTION_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
RAW_HTML_RETENTION_DAYS = int(os.environ.get("RAW_HTML_RETENTION_DAYS", "90"))
RAW_JSON_RETENTION_DAYS = int(os.environ.get("RAW_JSON_RETENTION_DAYS", "365"))


def _run_cleanup() -> dict[str, int]:
    now = datetime.now(timezone.utc)
    log_cutoff = now - timedelta(days=PROCESSING_LOG_RETENTION_DAYS)
    raw_cutoff = now - timedelta(days=RAW_ITEM_RETENTION_DAYS)
    html_cutoff = now - timedelta(days=RAW_HTML_RETENTION_DAYS)
    json_cutoff = now - timedelta(days=RAW_JSON_RETENTION_DAYS)

    deleted_logs = 0
    deleted_raw = 0
    deleted_raw_html = 0
    deleted_raw_json = 0
    minio_error = None

    if MINIO_RETENTION_ENABLED:
        try:
            deleted_raw_html = delete_objects_older_than("raw_html/", html_cutoff)
            deleted_raw_json = delete_objects_older_than("raw_json/", json_cutoff)
        except Exception as exc:
            minio_error = str(exc)
            log.warning("cleanup_minio_retention_failed", error=minio_error)

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
                "minio_retention_enabled": MINIO_RETENTION_ENABLED,
            },
        )
        session.add(job)
        session.flush()

        deleted_logs = session.execute(
            delete(ProcessingLog).where(ProcessingLog.created_at < log_cutoff)
        ).rowcount or 0

        deleted_raw = session.execute(
            delete(RawItem)
            .where(RawItem.created_at < raw_cutoff)
            .where(RawItem.status.in_(["duplicate", "failed"]))
        ).rowcount or 0

        job.deleted_count = int(deleted_logs + deleted_raw + deleted_raw_html + deleted_raw_json)
        job.status = "warning" if minio_error else "success"
        job.details = {
            **(job.details or {}),
            "deleted_logs": int(deleted_logs),
            "deleted_raw_items": int(deleted_raw),
            "deleted_raw_html_objects": int(deleted_raw_html),
            "deleted_raw_json_objects": int(deleted_raw_json),
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
            ),
        )

    return {
        "deleted_logs": int(deleted_logs),
        "deleted_raw": int(deleted_raw),
        "deleted_raw_html": int(deleted_raw_html),
        "deleted_raw_json": int(deleted_raw_json),
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
