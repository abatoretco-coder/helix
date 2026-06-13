"""
Worker scheduler - periodically enqueues housekeeping jobs.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo

from app.storage.postgres import get_session, log_processing
from app.storage.redis_queue import enqueue
from app.utils.logging import get_logger, setup_logging

log = get_logger("worker.scheduler")

SCHEDULER_TICK_SECONDS = int(os.environ.get("SCHEDULER_TICK_SECONDS", "30"))
SCHEDULER_ENABLE_DAILY_BRIEFING = os.environ.get("SCHEDULER_ENABLE_DAILY_BRIEFING", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
SCHEDULER_TIMEZONE = os.environ.get("DAILY_BRIEFING_TIMEZONE", "Europe/Paris")
SCHEDULER_BRIEFING_HOUR = int(os.environ.get("DAILY_BRIEFING_HOUR", "7"))
SCHEDULER_BRIEFING_MINUTE = int(os.environ.get("DAILY_BRIEFING_MINUTE", "30"))
SCHEDULER_BRIEFING_CATEGORY = os.environ.get("SCHEDULER_BRIEFING_CATEGORY", "all")


def _local_now() -> datetime:
    return datetime.now(ZoneInfo(SCHEDULER_TIMEZONE))


def _enqueue_daily_briefing(now_local: datetime) -> str:
    payload = f"daily:{now_local.date().isoformat()}:{SCHEDULER_BRIEFING_CATEGORY}"
    enqueue("briefing", payload)
    with get_session() as session:
        log_processing(
            session,
            "scheduler",
            0,
            "scheduler",
            "success",
            f"queued briefing payload={payload}",
        )
    return payload


def main() -> None:
    setup_logging("worker.scheduler")
    log.info(
        "scheduler_worker_start",
        tick_seconds=SCHEDULER_TICK_SECONDS,
        daily_briefing_enabled=SCHEDULER_ENABLE_DAILY_BRIEFING,
        briefing_timezone=SCHEDULER_TIMEZONE,
        briefing_hour=SCHEDULER_BRIEFING_HOUR,
        briefing_minute=SCHEDULER_BRIEFING_MINUTE,
        briefing_category=SCHEDULER_BRIEFING_CATEGORY,
    )

    last_daily_briefing_date = None

    while True:
        try:
            if SCHEDULER_ENABLE_DAILY_BRIEFING:
                now_local = _local_now()
                should_enqueue = (
                    now_local.hour == SCHEDULER_BRIEFING_HOUR
                    and now_local.minute == SCHEDULER_BRIEFING_MINUTE
                    and last_daily_briefing_date != now_local.date()
                )
                if should_enqueue:
                    payload = _enqueue_daily_briefing(now_local)
                    last_daily_briefing_date = now_local.date()
                    log.info("scheduler_enqueued", queue="briefing", payload=payload)
        except Exception as exc:
            log.error("scheduler_loop_error", error=str(exc))

        time.sleep(SCHEDULER_TICK_SECONDS)


if __name__ == "__main__":
    main()
