import os
from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from meilisearch_python_sdk import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter()

MEILI_URL = os.environ.get("MEILI_URL", "http://meilisearch:7700")
MEILI_KEY  = os.environ.get("MEILI_MASTER_KEY", "")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
EMBED_MODEL = os.environ.get("EMBEDDING_MODEL", os.environ.get("EMBED_MODEL", "nomic-embed-text"))


@router.get("/")
async def search_articles(
    q: str = Query(..., min_length=1),
    category: Optional[str] = None,
    language: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = Query(20, le=100),
    offset: int = 0,
):
    filters = []
    if category:
        filters.append(f'category = "{category}"')
    if language:
        filters.append(f'language = "{language}"')
    if source:
        filters.append(f'source = "{source}"')

    filter_str = " AND ".join(filters) if filters else None

    async with AsyncClient(MEILI_URL, MEILI_KEY) as client:
        index = client.index("articles")
        result = await index.search(
            q,
            limit=limit,
            offset=offset,
            filter=filter_str,
            attributes_to_highlight=["title", "summary_short"],
            attributes_to_retrieve=[
                "id", "title", "url", "source", "published_at",
                "language", "category", "summary_short", "final_score",
            ],
        )

    return {
        "query": q,
        "hits": result.hits,
        "total": result.estimated_total_hits,
        "limit": limit,
        "offset": offset,
    }


@router.get("/semantic")
async def semantic_search_articles(
    q: str = Query(..., min_length=1),
    category: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": q},
        )
    if resp.status_code != 200:
        raise HTTPException(502, "Embedding service unavailable")

    query_embedding = resp.json().get("embedding")
    if not query_embedding:
        return {"query": q, "hits": [], "total": 0, "limit": limit}

    filters = []
    params: dict[str, object] = {
        "emb": "[" + ",".join(str(x) for x in query_embedding) + "]",
        "limit": limit,
    }
    if category:
        filters.append("ai.category = :category")
        params["category"] = category
    if language:
        filters.append("a.language = :language")
        params["language"] = language

    where_extra = (" AND " + " AND ".join(filters)) if filters else ""
    sql = text(
        f"""
        SELECT a.id, a.title, a.url, a.published_at, a.language,
               s.name AS source, ai.summary_short, ai.category, ai.final_score,
               ai.embedding <=> :emb AS distance
        FROM article_ai ai
        JOIN articles a ON a.id = ai.article_id
        LEFT JOIN sources s ON s.id = a.source_id
        WHERE ai.embedding IS NOT NULL
        {where_extra}
        ORDER BY ai.embedding <=> :emb
        LIMIT :limit
        """
    )
    rows = (await db.execute(sql, params)).all()
    hits = [
        {
            "id": int(row.id),
            "title": row.title,
            "url": row.url,
            "source": row.source,
            "published_at": row.published_at.isoformat() if row.published_at else None,
            "language": row.language,
            "category": row.category,
            "summary_short": row.summary_short,
            "final_score": float(row.final_score or 0),
            "distance": float(row.distance),
            "similarity": max(0.0, min(1.0, 1.0 - float(row.distance))),
        }
        for row in rows
    ]

    return {"query": q, "hits": hits, "total": len(hits), "limit": limit}
