from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Cluster, ArticleCluster, Article
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
