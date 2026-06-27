from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Article, RawItem, Source
from app.schemas.sources import SourceRead, SourceCreate, SourceUpdate

router = APIRouter()


def _health_status(
    enabled: bool,
    error_count: int,
    items_24h: int,
    items_7d: int,
    success_rate_24h: float | None,
    conversion_rate_24h: float | None,
    last_success_at,
) -> str:
    if not enabled:
        return "disabled"
    if error_count >= 20:
        return "broken"
    if last_success_at is None and items_7d == 0:
        return "broken"
    if last_success_at is not None and last_success_at < datetime.utcnow() - timedelta(days=7):
        return "broken"
    if success_rate_24h is not None and success_rate_24h < 0.5:
        return "warning"
    if conversion_rate_24h is not None and items_24h >= 5 and conversion_rate_24h < 0.4:
        return "warning"
    if error_count > 0:
        return "warning"
    return "ok"


def _health_score(
    enabled: bool,
    error_count: int,
    items_7d: int,
    errors_7d: int,
    success_rate_7d: float | None,
    conversion_rate_7d: float | None,
    quality_avg: float | None,
    language_mismatch_rate_7d: float | None,
    last_success_at,
) -> int:
    if not enabled:
        return 0

    score = 100
    score -= min(error_count * 2, 30)
    score -= min(errors_7d * 4, 35)

    if items_7d == 0:
        score -= 30
    if success_rate_7d is not None:
        score -= int((1 - success_rate_7d) * 30)
    if conversion_rate_7d is not None:
        score -= int((1 - conversion_rate_7d) * 20)
    if quality_avg is not None:
        score += min(max(int((quality_avg - 50) / 5), -10), 10)
    if language_mismatch_rate_7d is not None:
        score -= int(language_mismatch_rate_7d * 20)
    if last_success_at is None:
        score -= 25
    elif last_success_at < datetime.utcnow() - timedelta(days=3):
        score -= 15

    return max(0, min(100, score))


def _quality_band(
    *,
    enabled: bool,
    health_score: int,
    items_7d: int,
    errors_7d: int,
    quality_avg: float | None,
    conversion_rate_7d: float | None,
    last_success_at,
) -> str:
    if not enabled:
        return "disabled"
    if health_score < 35:
        return "broken"
    if last_success_at is None or last_success_at < datetime.utcnow() - timedelta(days=7):
        return "stale"
    if items_7d >= 20 and errors_7d <= 2 and (quality_avg or 0) >= 60 and (conversion_rate_7d or 0) >= 0.6:
        return "high_value"
    if items_7d >= 40 and (quality_avg or 0) < 45:
        return "noisy"
    if health_score < 70:
        return "watch"
    return "healthy"


def _diagnostics(
    *,
    enabled: bool,
    error_count: int,
    items_24h: int,
    items_7d: int,
    errors_24h: int,
    errors_7d: int,
    success_rate_24h: float | None,
    conversion_rate_24h: float | None,
    language_mismatch_rate_7d: float | None,
    last_success_at,
) -> list[str]:
    reasons: list[str] = []
    if not enabled:
        reasons.append("Source disabled")
    if error_count >= 20:
        reasons.append("High accumulated error count")
    if errors_24h > 0:
        reasons.append(f"{errors_24h} raw item errors in the last 24h")
    elif errors_7d > 0:
        reasons.append(f"{errors_7d} raw item errors in the last 7d")
    if items_7d == 0:
        reasons.append("No new raw items in the last 7d")
    elif items_24h == 0:
        reasons.append("No new raw items in the last 24h")
    if success_rate_24h is not None and success_rate_24h < 0.5:
        reasons.append("Low article extraction success rate in the last 24h")
    if conversion_rate_24h is not None and items_24h >= 5 and conversion_rate_24h < 0.4:
        reasons.append("Many collected items did not become articles in the last 24h")
    if language_mismatch_rate_7d is not None and language_mismatch_rate_7d >= 0.25:
        reasons.append("Detected article languages often differ from source language")
    if last_success_at is None:
        reasons.append("Never collected successfully")
    elif last_success_at < datetime.utcnow() - timedelta(days=7):
        reasons.append("Last successful collection is older than 7 days")
    if not reasons:
        reasons.append("Collection and extraction look healthy")
    return reasons


def _recommendation(
    *,
    enabled: bool,
    priority: int,
    status: str,
    quality_band: str,
    health_score: int,
    items_7d: int,
    errors_7d: int,
    conversion_rate_7d: float | None,
    quality_avg: float | None,
    language_mismatch_rate_7d: float | None,
    last_success_at,
) -> dict:
    if not enabled:
        return {
            "action": "keep_disabled",
            "severity": "low",
            "title": "Keep disabled",
            "detail": "This source is disabled, so it does not consume collection or extraction capacity.",
            "target_priority": None,
        }

    if status == "broken" or health_score < 35:
        return {
            "action": "disable",
            "severity": "high",
            "title": "Disable or replace",
            "detail": "The source is broken or has a very low health score; disable it unless it is strategically important.",
            "target_priority": None,
        }

    if last_success_at is None or last_success_at < datetime.utcnow() - timedelta(days=7):
        return {
            "action": "refresh_or_disable",
            "severity": "high",
            "title": "Refresh, then disable if still stale",
            "detail": "The source has not succeeded recently. Force a refresh and retire it if the next cycle does not recover.",
            "target_priority": None,
        }

    if language_mismatch_rate_7d is not None and language_mismatch_rate_7d >= 0.35:
        return {
            "action": "review_language",
            "severity": "medium",
            "title": "Review language metadata",
            "detail": "Extracted article languages often differ from the configured source language, which can weaken filters and briefings.",
            "target_priority": None,
        }

    if quality_band == "noisy" or (
        items_7d >= 40
        and ((quality_avg or 0) < 45 or (conversion_rate_7d is not None and conversion_rate_7d < 0.45))
    ):
        return {
            "action": "lower_priority",
            "severity": "medium",
            "title": "Lower priority",
            "detail": "This source produces volume but relatively weak article output; slow it down before disabling it.",
            "target_priority": min(max(priority + 1, 1), 4),
        }

    if errors_7d >= 5:
        return {
            "action": "monitor_errors",
            "severity": "medium",
            "title": "Monitor errors",
            "detail": "The source still produces data, but recent raw item errors deserve a retry/reset check.",
            "target_priority": None,
        }

    if quality_band == "high_value" and priority > 1:
        return {
            "action": "boost_priority",
            "severity": "low",
            "title": "Boost priority",
            "detail": "This source has strong output and can be collected more often.",
            "target_priority": max(priority - 1, 1),
        }

    if items_7d == 0:
        return {
            "action": "watch_stale",
            "severity": "medium",
            "title": "Watch for staleness",
            "detail": "No new items were collected in the last 7 days; keep it only if the feed is intentionally low-frequency.",
            "target_priority": None,
        }

    return {
        "action": "keep",
        "severity": "low",
        "title": "Keep as is",
        "detail": "The source is producing acceptable data for its current priority.",
        "target_priority": None,
    }


def _recommendation_rank(row: dict) -> tuple[int, int, int]:
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    action_rank = {
        "disable": 0,
        "refresh_or_disable": 1,
        "lower_priority": 2,
        "review_language": 3,
        "monitor_errors": 4,
        "boost_priority": 5,
        "watch_stale": 6,
        "keep_disabled": 7,
        "keep": 8,
    }
    recommendation = row.get("recommendation") or {}
    return (
        severity_rank.get(str(recommendation.get("severity")), 9),
        action_rank.get(str(recommendation.get("action")), 9),
        -int(row.get("items_7d") or 0),
    )


async def _source_health_rows(db: AsyncSession, source_id: int | None = None) -> list[dict]:
    cutoff_24h = datetime.utcnow() - timedelta(hours=24)
    cutoff_7d = datetime.utcnow() - timedelta(days=7)

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
                .where(RawItem.created_at >= cutoff_24h)
                .group_by(RawItem.source_id)
            )
        ).all()
    }
    raw_counts_7d = {
        row.source_id: row.count
        for row in (
            await db.execute(
                select(RawItem.source_id, func.count().label("count"))
                .where(RawItem.source_id.in_(source_ids))
                .where(RawItem.created_at >= cutoff_7d)
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
                .where(RawItem.updated_at >= cutoff_24h)
                .group_by(RawItem.source_id)
            )
        ).all()
    }
    raw_errors_7d = {
        row.source_id: row.count
        for row in (
            await db.execute(
                select(RawItem.source_id, func.count().label("count"))
                .where(RawItem.source_id.in_(source_ids))
                .where(RawItem.status == "error")
                .where(RawItem.updated_at >= cutoff_7d)
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
                .where(Article.extracted_at >= cutoff_24h)
                .group_by(Article.source_id)
            )
        ).all()
    }
    articles_7d = {
        row.source_id: row.count
        for row in (
            await db.execute(
                select(Article.source_id, func.count().label("count"))
                .where(Article.source_id.in_(source_ids))
                .where(Article.extracted_at >= cutoff_7d)
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
                .where(Article.extracted_at >= cutoff_24h)
                .where(Article.extraction_status == "success")
                .group_by(Article.source_id)
            )
        ).all()
    }
    article_success_7d = {
        row.source_id: row.count
        for row in (
            await db.execute(
                select(Article.source_id, func.count().label("count"))
                .where(Article.source_id.in_(source_ids))
                .where(Article.extracted_at >= cutoff_7d)
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
    article_languages_7d = (
        await db.execute(
            select(Article.source_id, Article.language, func.count().label("count"))
            .where(Article.source_id.in_(source_ids))
            .where(Article.extracted_at >= cutoff_7d)
            .where(Article.language.isnot(None))
            .group_by(Article.source_id, Article.language)
        )
    ).all()

    language_counts_7d: dict[int, dict[str, int]] = {}
    for row in article_languages_7d:
        language = str(row.language or "").strip().lower()
        if not language:
            continue
        language_counts_7d.setdefault(row.source_id, {})[language] = int(row.count)

    rows: list[dict] = []
    for source in sources:
        total_items = int(raw_counts_24h.get(source.id, 0))
        total_items_7d = int(raw_counts_7d.get(source.id, 0))
        total_articles = int(articles_24h.get(source.id, 0))
        total_articles_7d = int(articles_7d.get(source.id, 0))
        success_articles = int(article_success_24h.get(source.id, 0))
        success_articles_7d = int(article_success_7d.get(source.id, 0))
        success_rate = (success_articles / total_articles) if total_articles else None
        success_rate_7d = (success_articles_7d / total_articles_7d) if total_articles_7d else None
        conversion_rate_24h = (total_articles / total_items) if total_items else None
        conversion_rate_7d = (total_articles_7d / total_items_7d) if total_items_7d else None
        source_language = str(source.language or "").strip().lower()
        language_counts = language_counts_7d.get(source.id, {})
        language_total_7d = sum(language_counts.values())
        language_mismatch_rate = None
        dominant_language = None
        if language_total_7d:
            dominant_language = max(language_counts.items(), key=lambda item: item[1])[0]
            if source_language:
                mismatch_count = language_total_7d - language_counts.get(source_language, 0)
                language_mismatch_rate = mismatch_count / language_total_7d

        avg_quality_value = (
            round(float(avg_quality.get(source.id, 0) or 0), 3)
            if avg_quality.get(source.id) is not None
            else None
        )
        health_score = _health_score(
            bool(source.enabled),
            int(source.error_count or 0),
            total_items_7d,
            int(raw_errors_7d.get(source.id, 0)),
            success_rate_7d,
            conversion_rate_7d,
            avg_quality_value,
            language_mismatch_rate,
            source.last_success_at,
        )
        quality_band = _quality_band(
            enabled=bool(source.enabled),
            health_score=health_score,
            items_7d=total_items_7d,
            errors_7d=int(raw_errors_7d.get(source.id, 0)),
            quality_avg=avg_quality_value,
            conversion_rate_7d=conversion_rate_7d,
            last_success_at=source.last_success_at,
        )
        status = _health_status(
            bool(source.enabled),
            int(source.error_count or 0),
            total_items,
            total_items_7d,
            success_rate,
            conversion_rate_24h,
            source.last_success_at,
        )

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
                "errors_7d": int(raw_errors_7d.get(source.id, 0)),
                "items_24h": total_items,
                "items_7d": total_items_7d,
                "articles_24h": total_articles,
                "articles_7d": total_articles_7d,
                "extraction_success_rate_24h": round(success_rate, 3) if success_rate is not None else None,
                "extraction_success_rate_7d": round(success_rate_7d, 3) if success_rate_7d is not None else None,
                "article_conversion_rate_24h": round(conversion_rate_24h, 3) if conversion_rate_24h is not None else None,
                "article_conversion_rate_7d": round(conversion_rate_7d, 3) if conversion_rate_7d is not None else None,
                "quality_avg": avg_quality_value,
                "health_score": health_score,
                "quality_band": quality_band,
                "dominant_article_language_7d": dominant_language,
                "language_mismatch_rate_7d": (
                    round(language_mismatch_rate, 3) if language_mismatch_rate is not None else None
                ),
                "recommendation": _recommendation(
                    enabled=bool(source.enabled),
                    priority=int(source.priority or 3),
                    status=status,
                    quality_band=quality_band,
                    health_score=health_score,
                    items_7d=total_items_7d,
                    errors_7d=int(raw_errors_7d.get(source.id, 0)),
                    conversion_rate_7d=conversion_rate_7d,
                    quality_avg=avg_quality_value,
                    language_mismatch_rate_7d=language_mismatch_rate,
                    last_success_at=source.last_success_at,
                ),
                "diagnostics": _diagnostics(
                    enabled=bool(source.enabled),
                    error_count=int(source.error_count or 0),
                    items_24h=total_items,
                    items_7d=total_items_7d,
                    errors_24h=int(raw_errors_24h.get(source.id, 0)),
                    errors_7d=int(raw_errors_7d.get(source.id, 0)),
                    success_rate_24h=success_rate,
                    conversion_rate_24h=conversion_rate_24h,
                    language_mismatch_rate_7d=language_mismatch_rate,
                    last_success_at=source.last_success_at,
                ),
                "status": status,
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


@router.get("/recommendations")
async def source_recommendations(db: AsyncSession = Depends(get_db), limit: int = Query(50, ge=1, le=200)):
    rows = await _source_health_rows(db)
    actionable = [
        row
        for row in rows
        if (row.get("recommendation") or {}).get("action") not in {"keep", "keep_disabled"}
    ]
    actionable.sort(key=_recommendation_rank)
    limited_rows = actionable[:limit]
    by_action = {
        action: sum(1 for row in actionable if (row.get("recommendation") or {}).get("action") == action)
        for action in sorted({(row.get("recommendation") or {}).get("action") for row in actionable})
    }
    return {
        "count": len(limited_rows),
        "total_actionable": len(actionable),
        "by_action": by_action,
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


@router.post("/{source_id}/enable", response_model=SourceRead)
async def enable_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    source.enabled = True
    await db.commit()
    await db.refresh(source)
    return source


@router.post("/{source_id}/disable", response_model=SourceRead)
async def disable_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    source.enabled = False
    await db.commit()
    await db.refresh(source)
    return source


@router.post("/{source_id}/refresh", response_model=SourceRead)
async def refresh_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    # Move last_checked_at backward so the collector picks the source on next cycle.
    source.last_checked_at = datetime.utcnow() - timedelta(minutes=max(int(source.refresh_minutes or 60), 1) + 1)
    await db.commit()
    await db.refresh(source)
    return source


@router.post("/{source_id}/reset-errors", response_model=SourceRead)
async def reset_source_errors(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    source.error_count = 0
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
