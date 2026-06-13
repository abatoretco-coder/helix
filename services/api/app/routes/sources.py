from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Article, RawItem, Source
from app.schemas.sources import SourceRead, SourceCreate, SourceUpdate

router = APIRouter()


def _health_status(enabled: bool, error_count: int, items_24h: int, success_rate_24h: float | None, last_success_at) -> str:
    if not enabled:
        return "warning"
    if error_count >= 20:
        return "broken"
    if last_success_at is None and items_24h == 0:
        return "broken"
    if success_rate_24h is not None and success_rate_24h < 0.5:
        return "warning"
    if error_count > 0:
        return "warning"
    return "ok"


async def _source_health_rows(db: AsyncSession, source_id: int | None = None) -> list[dict]:
    cutoff = datetime.utcnow() - timedelta(hours=24)

    source_query = select(Source)
    if source_id is not None:
        source_query = source_query.where(Source.id == source_id)
    sources = (await db.execute(source_query.order_by(Source.priority.asc(), Source.name.asc()))).scalars().all()
    source_ids = [source.id for source in sources]

    if not source_ids:
        return []

    raw_counts_24h = {
        row.source_id: row.count
        for row in (
            await db.execute(
                select(RawItem.source_id, func.count().label("count"))
                .where(RawItem.source_id.in_(source_ids))
                .where(RawItem.created_at >= cutoff)
                .group_by(RawItem.source_id)
            )
        ).all()
    }
    raw_errors_24h = {
        row.source_id: row.count
        for row in (
            await db.execute(
                select(RawItem.source_id, func.count().label("count"))
                .where(RawItem.source_id.in_(source_ids))
                .where(RawItem.status == "error")
                .where(RawItem.updated_at >= cutoff)
                .group_by(RawItem.source_id)
            )
        ).all()
    }
    last_error_at = {
        row.source_id: row.last_error_at
        for row in (
            await db.execute(
                select(RawItem.source_id, func.max(RawItem.updated_at).label("last_error_at"))
                .where(RawItem.source_id.in_(source_ids))
                .where(RawItem.status == "error")
                .group_by(RawItem.source_id)
            )
        ).all()
    }
    articles_24h = {
        row.source_id: row.count
        for row in (
            await db.execute(
                select(Article.source_id, func.count().label("count"))
                .where(Article.source_id.in_(source_ids))
                .where(Article.extracted_at >= cutoff)
                .group_by(Article.source_id)
            )
        ).all()
    }
    article_success_24h = {
        row.source_id: row.count
        for row in (
            await db.execute(
                select(Article.source_id, func.count().label("count"))
                .where(Article.source_id.in_(source_ids))
                .where(Article.extracted_at >= cutoff)
                .where(Article.extraction_status == "success")
                .group_by(Article.source_id)
            )
        ).all()
    }
    avg_quality = {
        row.source_id: row.avg_quality
        for row in (
            await db.execute(
                select(Article.source_id, func.avg(Article.quality_score).label("avg_quality"))
                .where(Article.source_id.in_(source_ids))
                .group_by(Article.source_id)
            )
        ).all()
    }

    rows: list[dict] = []
    for source in sources:
        total_items = int(raw_counts_24h.get(source.id, 0))
        total_articles = int(articles_24h.get(source.id, 0))
        success_articles = int(article_success_24h.get(source.id, 0))
        success_rate = (success_articles / total_articles) if total_articles else None

        rows.append(
            {
                "id": source.id,
                "name": source.name,
                "source_type": source.source_type,
                "category": source.category,
                "priority": source.priority,
                "enabled": source.enabled,
                "last_checked_at": source.last_checked_at.isoformat() if source.last_checked_at else None,
                "last_success_at": source.last_success_at.isoformat() if source.last_success_at else None,
                "last_error_at": last_error_at.get(source.id).isoformat() if last_error_at.get(source.id) else None,
                "error_count": source.error_count,
                "errors_24h": int(raw_errors_24h.get(source.id, 0)),
                "items_24h": total_items,
                "articles_24h": total_articles,
                "extraction_success_rate_24h": round(success_rate, 3) if success_rate is not None else None,
                "quality_avg": round(float(avg_quality.get(source.id, 0) or 0), 3) if avg_quality.get(source.id) is not None else None,
                "status": _health_status(source.enabled, int(source.error_count or 0), total_items, success_rate, source.last_success_at),
            }
        )

    return rows


@router.get("/", response_model=list[SourceRead])
async def list_sources(
    enabled: Optional[bool] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Source).order_by(Source.priority, Source.name)
    if enabled is not None:
        q = q.where(Source.enabled == enabled)
    if category:
        q = q.where(Source.category == category)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/health")
async def source_health(db: AsyncSession = Depends(get_db), limit: int = Query(100, ge=1, le=500)):
    rows = await _source_health_rows(db)
    limited_rows = rows[:limit]
    return {
        "count": len(limited_rows),
        "items": limited_rows,
    }


@router.get("/{source_id}/health")
async def source_health_detail(source_id: int, db: AsyncSession = Depends(get_db)):
    rows = await _source_health_rows(db, source_id=source_id)
    if not rows:
        raise HTTPException(404, "Source not found")
    return rows[0]


@router.get("/{source_id}", response_model=SourceRead)
async def get_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    return source


@router.post("/", response_model=SourceRead, status_code=201)
async def create_source(payload: SourceCreate, db: AsyncSession = Depends(get_db)):
    source = Source(**payload.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.patch("/{source_id}", response_model=SourceRead)
async def update_source(source_id: int, payload: SourceUpdate, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    await db.commit()
    await db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=204)
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    await db.delete(source)
    await db.commit()
