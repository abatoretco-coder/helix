from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Article, ArticleAI, ProcessingLog, RawItem, Source
from app.db.session import get_db

router = APIRouter()


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
        "generated_at": datetime.utcnow().isoformat() + "Z",
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


@router.get("/sources/status")
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
