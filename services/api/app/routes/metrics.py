from collections import Counter
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Article, ArticleAI, ArticleCluster, Briefing, Cluster, ProcessingLog, RawItem, Source
from app.db.session import get_db
from app.storage.redis_queue import queue_size

router = APIRouter()

PIPELINE_QUEUES = ("extract", "ai", "cluster", "briefing")


def _iso(value) -> str | None:
    return value.isoformat() if value else None


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


async def _count_today(db: AsyncSession, model, date_column) -> int:
    return (
        await db.execute(
            select(func.count())
            .select_from(model)
            .where(func.date(date_column) == func.current_date())
        )
    ).scalar_one()


async def _recent_error_rows(db: AsyncSession, limit: int = 50) -> list[Any]:
    rows = (
        await db.execute(
            select(
                ProcessingLog.id,
                ProcessingLog.item_type,
                ProcessingLog.item_id,
                ProcessingLog.step,
                ProcessingLog.status,
                ProcessingLog.message,
                ProcessingLog.duration_ms,
                ProcessingLog.created_at,
            )
            .where(ProcessingLog.status == "error")
            .order_by(ProcessingLog.created_at.desc())
            .limit(limit)
        )
    ).all()
    return list(rows)


async def _recent_duration_stats(db: AsyncSession) -> dict[str, float]:
    rows = (
        await db.execute(
            select(
                ProcessingLog.step,
                func.avg(ProcessingLog.duration_ms),
            )
            .where(ProcessingLog.duration_ms.is_not(None))
            .where(ProcessingLog.created_at >= text("now() - interval '24 hours'"))
            .group_by(ProcessingLog.step)
        )
    ).all()
    return {str(step): round(_safe_float(avg_ms), 2) for step, avg_ms in rows}


async def _queue_depths() -> dict[str, int]:
    return {queue_name: queue_size(queue_name) for queue_name in PIPELINE_QUEUES}


@router.get("/pipeline/metrics")
async def pipeline_metrics(db: AsyncSession = Depends(get_db)):
    total_sources = (await db.execute(select(func.count()).select_from(Source))).scalar_one()
    enabled_sources = (await db.execute(select(func.count()).select_from(Source).where(Source.enabled == True))).scalar_one()
    sources_in_error = (
        await db.execute(select(func.count()).select_from(Source).where(Source.error_count > 0))
    ).scalar_one()

    total_raw_items = (await db.execute(select(func.count()).select_from(RawItem))).scalar_one()
    total_articles = (await db.execute(select(func.count()).select_from(Article))).scalar_one()
    ai_processed = (await db.execute(select(func.count()).select_from(ArticleAI))).scalar_one()

    raw_status_rows = (
        await db.execute(
            select(RawItem.status, func.count()).group_by(RawItem.status).order_by(func.count().desc())
        )
    ).all()

    recent_failures = (
        await db.execute(
            select(func.count())
            .select_from(ProcessingLog)
            .where(ProcessingLog.status == "error")
            .where(ProcessingLog.created_at >= text("now() - interval '24 hours'"))
        )
    ).scalar_one()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "total": total_sources,
            "enabled": enabled_sources,
            "with_errors": sources_in_error,
        },
        "pipeline": {
            "raw_items_total": total_raw_items,
            "articles_total": total_articles,
            "ai_processed_total": ai_processed,
            "processing_errors_last_24h": recent_failures,
            "raw_items_by_status": {status or "unknown": count for status, count in raw_status_rows},
        },
    }


@router.get("/pipeline/status")
async def pipeline_status(db: AsyncSession = Depends(get_db)):
    total_sources = (await db.execute(select(func.count()).select_from(Source))).scalar_one()
    enabled_sources = (await db.execute(select(func.count()).select_from(Source).where(Source.enabled == True))).scalar_one()
    active_sources = (await db.execute(select(func.count()).select_from(Source).where(Source.enabled == True))).scalar_one()
    sources_in_error = (
        await db.execute(select(func.count()).select_from(Source).where(Source.error_count > 0))
    ).scalar_one()

    raw_items_total = (await db.execute(select(func.count()).select_from(RawItem))).scalar_one()
    raw_items_today = await _count_today(db, RawItem, RawItem.created_at)
    articles_total = (await db.execute(select(func.count()).select_from(Article))).scalar_one()
    articles_today = await _count_today(db, Article, Article.created_at)
    ai_total = (await db.execute(select(func.count()).select_from(ArticleAI))).scalar_one()
    ai_today = await _count_today(db, ArticleAI, ArticleAI.processed_at)
    briefings_total = (await db.execute(select(func.count()).select_from(Briefing))).scalar_one()
    briefings_today = await _count_today(db, Briefing, Briefing.generated_at)
    queue_depths = await _queue_depths()
    durations = await _recent_duration_stats(db)

    error_count_24h = (
        await db.execute(
            select(func.count())
            .select_from(ProcessingLog)
            .where(ProcessingLog.status == "error")
            .where(ProcessingLog.created_at >= text("now() - interval '24 hours'"))
        )
    ).scalar_one()

    cluster_count = (await db.execute(select(func.count()).select_from(Cluster))).scalar_one()
    cluster_links = (await db.execute(select(func.count()).select_from(ArticleCluster))).scalar_one()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "total": total_sources,
            "enabled": enabled_sources,
            "active": active_sources,
            "with_errors": sources_in_error,
        },
        "pipeline": {
            "raw_items_total": raw_items_total,
            "raw_items_today": raw_items_today,
            "articles_total": articles_total,
            "articles_today": articles_today,
            "ai_processed_total": ai_total,
            "ai_processed_today": ai_today,
            "briefings_total": briefings_total,
            "briefings_today": briefings_today,
            "processing_errors_last_24h": error_count_24h,
            "queue_depths": queue_depths,
            "average_durations_last_24h_ms": durations,
            "cluster_count": cluster_count,
            "cluster_links": cluster_links,
        },
    }


@router.get("/pipeline/queues")
async def pipeline_queues():
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "queues": await _queue_depths(),
    }


@router.get("/pipeline/errors")
async def pipeline_errors(db: AsyncSession = Depends(get_db), limit: int = Query(default=25, ge=1, le=100)):
    rows = await _recent_error_rows(db, limit=limit)
    step_counts = Counter(str(row.step) for row in rows)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "by_step": dict(step_counts),
        "items": [
            {
                "id": row.id,
                "item_type": row.item_type,
                "item_id": row.item_id,
                "step": row.step,
                "status": row.status,
                "message": row.message,
                "duration_ms": row.duration_ms,
                "created_at": _iso(row.created_at),
            }
            for row in rows
        ],
    }


@router.get("/pipeline/sources-status")
async def sources_status(
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(
                Source.id,
                Source.name,
                Source.source_type,
                Source.enabled,
                Source.last_checked_at,
                Source.last_success_at,
                Source.error_count,
                Source.refresh_minutes,
                Source.priority,
            )
            .order_by(Source.priority.asc(), Source.error_count.desc(), Source.name.asc())
            .limit(limit)
        )
    ).all()

    return {
        "count": len(rows),
        "items": [
            {
                "id": row.id,
                "name": row.name,
                "source_type": row.source_type,
                "enabled": row.enabled,
                "last_checked_at": row.last_checked_at.isoformat() if row.last_checked_at else None,
                "last_success_at": row.last_success_at.isoformat() if row.last_success_at else None,
                "error_count": row.error_count,
                "refresh_minutes": row.refresh_minutes,
                "priority": row.priority,
            }
            for row in rows
        ],
    }
