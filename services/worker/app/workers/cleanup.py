"""
Worker cleanup - runs periodic retention tasks for old logs and stale raw items.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from app.db.models import ProcessingLog, RawItem, RetentionJob
from app.storage.postgres import get_session, log_processing
from app.utils.logging import get_logger, setup_logging

log = get_logger("worker.cleanup")

CLEANUP_INTERVAL_SECONDS = int(os.environ.get("CLEANUP_INTERVAL_SECONDS", "3600"))
PROCESSING_LOG_RETENTION_DAYS = int(os.environ.get("PROCESSING_LOG_RETENTION_DAYS", "30"))
RAW_ITEM_RETENTION_DAYS = int(os.environ.get("RAW_ITEM_RETENTION_DAYS", "14"))


def _run_cleanup() -> dict[str, int]:
    now = datetime.now(timezone.utc)
    log_cutoff = now - timedelta(days=PROCESSING_LOG_RETENTION_DAYS)
    raw_cutoff = now - timedelta(days=RAW_ITEM_RETENTION_DAYS)

    deleted_logs = 0
    deleted_raw = 0

    with get_session() as session:
        job = RetentionJob(
            job_type="periodic_cleanup",
            status="running",
            cutoff_days=min(PROCESSING_LOG_RETENTION_DAYS, RAW_ITEM_RETENTION_DAYS),
            started_at=now,
            details={
                "processing_log_cutoff": log_cutoff.isoformat(),
                "raw_item_cutoff": raw_cutoff.isoformat(),
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

        job.deleted_count = int(deleted_logs + deleted_raw)
        job.status = "success"
        job.finished_at = datetime.now(timezone.utc)

        log_processing(
            session,
            "retention",
            int(job.id),
            "cleanup",
            "success",
            f"deleted_logs={deleted_logs} deleted_raw={deleted_raw}",
        )

    return {"deleted_logs": int(deleted_logs), "deleted_raw": int(deleted_raw)}


def main() -> None:
    setup_logging("worker.cleanup")
    log.info(
        "cleanup_worker_start",
        interval_seconds=CLEANUP_INTERVAL_SECONDS,
        processing_log_retention_days=PROCESSING_LOG_RETENTION_DAYS,
        raw_item_retention_days=RAW_ITEM_RETENTION_DAYS,
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
