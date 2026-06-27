from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, text
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Article, ArticleAI
from app.queue import enqueue
from app.schemas.articles import ArticleRead, ArticleDetail

router = APIRouter()


@router.get("/", response_model=list[ArticleRead])
async def list_articles(
    source_id: Optional[int] = None,
    category: Optional[str] = None,
    language: Optional[str] = None,
    min_score: Optional[float] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(Article)
        .outerjoin(ArticleAI, Article.id == ArticleAI.article_id)
        .order_by(desc(Article.published_at))
        .limit(limit)
        .offset(offset)
        .options(selectinload(Article.ai))
    )
    if source_id:
        q = q.where(Article.source_id == source_id)
    if language:
        q = q.where(Article.language == language)
    if category:
        q = q.where(ArticleAI.category == category)
    if min_score is not None:
        q = q.where(ArticleAI.final_score >= min_score)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{article_id}", response_model=ArticleDetail)
async def get_article(article_id: int, db: AsyncSession = Depends(get_db)):
    q = (
        select(Article)
        .where(Article.id == article_id)
        .options(selectinload(Article.ai), selectinload(Article.source))
    )
    result = await db.execute(q)
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")
    return article


@router.get("/{article_id}/similar")
async def get_similar_articles(
    article_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Article not found")

    sql = text(
        """
        SELECT a.id,
               a.title,
               a.url,
               a.published_at,
               s.name AS source_name,
               ai.summary_short,
               ai.category,
               ai.final_score,
               ai.embedding <=> base.embedding AS distance
        FROM article_ai base
        JOIN article_ai ai ON ai.article_id <> base.article_id
        JOIN articles a ON a.id = ai.article_id
        LEFT JOIN sources s ON s.id = a.source_id
        WHERE base.article_id = :article_id
          AND base.embedding IS NOT NULL
          AND ai.embedding IS NOT NULL
        ORDER BY ai.embedding <=> base.embedding
        LIMIT :limit
        """
    )
    rows = (await db.execute(sql, {"article_id": article_id, "limit": limit})).all()
    if not rows:
        return {"article_id": article_id, "count": 0, "items": []}

    return {
        "article_id": article_id,
        "count": len(rows),
        "items": [
            {
                "id": int(row.id),
                "title": row.title,
                "url": row.url,
                "source": row.source_name,
                "published_at": row.published_at.isoformat() if row.published_at else None,
                "summary_short": row.summary_short,
                "category": row.category,
                "final_score": float(row.final_score or 0),
                "distance": float(row.distance),
                "similarity": max(0.0, min(1.0, 1.0 - float(row.distance))),
            }
            for row in rows
        ],
    }


@router.post("/{article_id}/reprocess", status_code=202)
async def reprocess_article(article_id: int, db: AsyncSession = Depends(get_db)):
    """Push article back to the AI queue for reprocessing."""
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(404, "Article not found")
    await enqueue("ai", str(article_id))
    return {"queued": article_id}
