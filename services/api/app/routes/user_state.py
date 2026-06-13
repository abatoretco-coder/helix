from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Article, ArticleAI, ArticleUserState, Source
from app.db.session import get_db

router = APIRouter()


class UserStateUpdatePayload(BaseModel):
    profile_id: str = "default"
    is_read: bool | None = None
    is_saved: bool | None = None
    is_hidden: bool | None = None


@router.get("/")
async def list_user_states(
    profile_id: str = Query(default="default"),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(ArticleUserState)
            .where(ArticleUserState.profile_id == profile_id)
            .order_by(desc(ArticleUserState.updated_at))
            .limit(limit)
        )
    ).scalars().all()
    return {
        "profile_id": profile_id,
        "count": len(rows),
        "items": [
            {
                "article_id": int(row.article_id),
                "is_read": bool(row.is_read),
                "is_saved": bool(row.is_saved),
                "is_hidden": bool(row.is_hidden),
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ],
    }


@router.post("/articles/{article_id}")
async def upsert_article_user_state(
    article_id: int,
    payload: UserStateUpdatePayload,
    db: AsyncSession = Depends(get_db),
):
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    existing = (
        await db.execute(
            select(ArticleUserState).where(
                and_(
                    ArticleUserState.profile_id == payload.profile_id,
                    ArticleUserState.article_id == article_id,
                )
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        existing = ArticleUserState(
            profile_id=payload.profile_id,
            article_id=article_id,
            is_read=bool(payload.is_read) if payload.is_read is not None else False,
            is_saved=bool(payload.is_saved) if payload.is_saved is not None else False,
            is_hidden=bool(payload.is_hidden) if payload.is_hidden is not None else False,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(existing)
    else:
        if payload.is_read is not None:
            existing.is_read = bool(payload.is_read)
        if payload.is_saved is not None:
            existing.is_saved = bool(payload.is_saved)
        if payload.is_hidden is not None:
            existing.is_hidden = bool(payload.is_hidden)
        existing.updated_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "profile_id": payload.profile_id,
        "article_id": article_id,
        "is_read": bool(existing.is_read),
        "is_saved": bool(existing.is_saved),
        "is_hidden": bool(existing.is_hidden),
        "updated_at": existing.updated_at.isoformat() if existing.updated_at else None,
    }


@router.get("/saved")
async def get_saved_articles(
    profile_id: str = Query(default="default"),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    article_date = func.coalesce(Article.published_at, Article.discovered_at, Article.extracted_at)
    rows = (
        await db.execute(
            select(
                Article.id,
                Article.title,
                Article.url,
                article_date.label("article_date"),
                ArticleAI.summary_short,
                ArticleAI.category,
                ArticleAI.final_score,
                Source.name.label("source_name"),
            )
            .join(ArticleUserState, ArticleUserState.article_id == Article.id)
            .outerjoin(ArticleAI, ArticleAI.article_id == Article.id)
            .outerjoin(Source, Source.id == Article.source_id)
            .where(ArticleUserState.profile_id == profile_id)
            .where(ArticleUserState.is_saved.is_(True))
            .order_by(desc(article_date))
            .limit(limit)
        )
    ).all()

    return {
        "profile_id": profile_id,
        "count": len(rows),
        "items": [
            {
                "id": int(row.id),
                "title": row.title,
                "url": row.url,
                "source": row.source_name,
                "published_at": row.article_date.isoformat() if row.article_date else None,
                "summary_short": row.summary_short,
                "category": row.category,
                "final_score": float(row.final_score or 0),
            }
            for row in rows
        ],
    }
