from collections import Counter
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis_async

from app.db.models import Article, ArticleAI, ArticleCluster, Briefing, Cluster, OpenAIUsageEvent, ProcessingLog, RawItem, Source
from app.db.session import get_db
from app.openai_usage import configured_limits
from app.queue import dead_queue_size

router = APIRouter()

PIPELINE_QUEUES = ("extract", "ai", "cluster", "briefing")
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
_redis_client = None


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
    global _redis_client
    try:
        if _redis_client is None:
            _redis_client = redis_async.from_url(REDIS_URL, decode_responses=True)
        return {queue_name: int(await _redis_client.llen(f"queue:{queue_name}")) for queue_name in PIPELINE_QUEUES}
    except Exception:
        return {queue_name: 0 for queue_name in PIPELINE_QUEUES}


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


@router.get("/ops/summary")
async def ops_summary(db: AsyncSession = Depends(get_db)):
    status = await pipeline_status(db)
    queues = await pipeline_queues()
    errors = await pipeline_errors(db, limit=10)
    source_rows = (
        await db.execute(
            select(Source.enabled, Source.error_count)
        )
    ).all()
    source_summary = {
        "total": len(source_rows),
        "enabled": sum(1 for enabled, _ in source_rows if enabled),
        "disabled": sum(1 for enabled, _ in source_rows if not enabled),
        "with_errors": sum(1 for _, error_count in source_rows if int(error_count or 0) > 0),
        "high_error": sum(1 for _, error_count in source_rows if int(error_count or 0) >= 20),
    }

    backup_dir = Path(os.environ.get("BACKUP_DIR", "backups"))
    obsidian_path = Path(os.environ.get("OBSIDIAN_EXPORT_PATH", "exports/obsidian"))
    dead_depths = {queue_name: await dead_queue_size(queue_name) for queue_name in PIPELINE_QUEUES}

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "queues": queues,
        "dead_letter": {
            "queues": dead_depths,
            "total": sum(dead_depths.values()),
        },
        "recent_errors_count": errors.get("count", 0),
        "recent_errors": errors,
        "source_health_summary": source_summary,
        "configured_models": {
            "llm_provider": os.environ.get("LLM_PROVIDER", "openai"),
            "llm_model": os.environ.get("OPENAI_MODEL", os.environ.get("LLM_MODEL", "gpt-4.1-mini")),
            "embedding_model": os.environ.get("OPENAI_EMBEDDING_MODEL", os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")),
        },
        "low_power_mode": os.environ.get("LOW_POWER_MODE", "false").strip().lower() in {"1", "true", "yes", "on"},
        "backup": {
            "path": str(backup_dir),
            "exists": backup_dir.exists(),
        },
        "obsidian_export": {
            "enabled": os.environ.get("OBSIDIAN_EXPORT_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"},
            "path": str(obsidian_path),
            "exists": obsidian_path.exists(),
        },
    }


@router.get("/ops/openai-usage")
async def openai_usage(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Return persisted usage for calls that an API client explicitly requested."""
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    rows = (
        await db.execute(
            select(
                OpenAIUsageEvent.endpoint,
                OpenAIUsageEvent.operation,
                OpenAIUsageEvent.model,
                OpenAIUsageEvent.status,
                func.count().label("requests"),
                func.coalesce(func.sum(OpenAIUsageEvent.input_tokens), 0).label("input_tokens"),
                func.coalesce(func.sum(OpenAIUsageEvent.output_tokens), 0).label("output_tokens"),
            )
            .where(OpenAIUsageEvent.created_at >= since)
            .group_by(
                OpenAIUsageEvent.endpoint,
                OpenAIUsageEvent.operation,
                OpenAIUsageEvent.model,
                OpenAIUsageEvent.status,
            )
            .order_by(OpenAIUsageEvent.endpoint, OpenAIUsageEvent.operation, OpenAIUsageEvent.status)
        )
    ).all()
    total_requests = sum(int(row.requests) for row in rows)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "since": since.replace(tzinfo=timezone.utc).isoformat(),
        "days": days,
        "usage_policy": "explicit_api_requests_only",
        "limits": configured_limits(),
        "total_requests": total_requests,
        "breakdown": [
            {
                "endpoint": row.endpoint,
                "operation": row.operation,
                "model": row.model,
                "status": row.status,
                "requests": int(row.requests),
                "input_tokens": int(row.input_tokens),
                "output_tokens": int(row.output_tokens),
            }
            for row in rows
        ],
    }
