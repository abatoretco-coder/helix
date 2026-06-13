from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Article, ArticleAI, ArticleCluster, Cluster, Source
from app.schemas.clusters import ClusterRead, ClusterDetail

router = APIRouter()


@router.get("/", response_model=list[ClusterRead])
async def list_clusters(
    topic: Optional[str] = None,
    limit: int = Query(30, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    q = select(Cluster).order_by(desc(Cluster.last_seen_at)).limit(limit).offset(offset)
    if topic:
        q = q.where(Cluster.topic == topic)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{cluster_id}", response_model=ClusterDetail)
async def get_cluster(cluster_id: int, db: AsyncSession = Depends(get_db)):
    cluster = await db.get(Cluster, cluster_id)
    if not cluster:
        raise HTTPException(404, "Cluster not found")

    # Load articles in this cluster
    q = (
        select(Article)
        .join(ArticleCluster, Article.id == ArticleCluster.article_id)
        .where(ArticleCluster.cluster_id == cluster_id)
        .order_by(desc(Article.published_at))
        .options(selectinload(Article.ai))
    )
    result = await db.execute(q)
    articles = result.scalars().all()

    return {"cluster": cluster, "articles": articles}


@router.get("/{cluster_id}/timeline")
async def get_cluster_timeline(cluster_id: int, db: AsyncSession = Depends(get_db)):
    cluster = await db.get(Cluster, cluster_id)
    if not cluster:
        raise HTTPException(404, "Cluster not found")

    timeline_date = func.coalesce(Article.published_at, Article.discovered_at, Article.extracted_at).label("timeline_date")
    rows = (
        await db.execute(
            select(
                Article.id,
                Article.title,
                Article.url,
                timeline_date,
                Source.name.label("source_name"),
                ArticleAI.summary_short,
                ArticleAI.final_score,
            )
            .join(ArticleCluster, ArticleCluster.article_id == Article.id)
            .outerjoin(ArticleAI, ArticleAI.article_id == Article.id)
            .outerjoin(Source, Source.id == Article.source_id)
            .where(ArticleCluster.cluster_id == cluster_id)
            .order_by(asc(timeline_date))
        )
    ).all()

    return {
        "cluster_id": cluster_id,
        "count": len(rows),
        "items": [
            {
                "id": row.id,
                "title": row.title,
                "url": row.url,
                "published_at": row.timeline_date.isoformat() if row.timeline_date else None,
                "source": row.source_name,
                "summary_short": row.summary_short,
                "final_score": float(row.final_score or 0),
            }
            for row in rows
        ],
    }
