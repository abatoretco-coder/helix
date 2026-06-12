import os
from typing import Optional
from fastapi import APIRouter, Query
from meilisearch_python_sdk import AsyncClient

router = APIRouter()

MEILI_URL = os.environ.get("MEILI_URL", "http://meilisearch:7700")
MEILI_KEY  = os.environ.get("MEILI_MASTER_KEY", "")


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
