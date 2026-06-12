import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.db.session import get_db
from app.db.models import Article, ArticleAI
from app.schemas.articles import ArticleRead

router = APIRouter()

OLLAMA_URL   = os.environ.get("OLLAMA_URL", "http://ollama:11434")
EMBED_MODEL  = os.environ.get("EMBED_MODEL", "nomic-embed-text")
LLM_MODEL    = os.environ.get("LLM_MODEL", "mistral")


class JarvisQuery(BaseModel):
    query: str
    date_range: str = "today"   # today, week, month, all
    categories: list[str] = []
    limit: int = 10


@router.post("/query")
async def jarvis_query(payload: JarvisQuery, db: AsyncSession = Depends(get_db)):
    # 1. Generate embedding for the query
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": payload.query},
        )
    if resp.status_code != 200:
        raise HTTPException(502, "Embedding service unavailable")
    query_embedding = resp.json()["embedding"]

    # 2. Vector search against article_ai
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    sql = text("""
        SELECT a.id, a.title, a.url, a.published_at, a.language,
               ai.summary_short, ai.category, ai.final_score,
               ai.embedding <=> :emb AS distance
        FROM article_ai ai
        JOIN articles a ON a.id = ai.article_id
        WHERE ai.embedding IS NOT NULL
        ORDER BY ai.embedding <=> :emb
        LIMIT :limit
    """)
    result = await db.execute(sql, {"emb": embedding_str, "limit": payload.limit})
    rows = result.fetchall()

    articles = [
        {
            "id": r.id,
            "title": r.title,
            "url": r.url,
            "published_at": r.published_at.isoformat() if r.published_at else None,
            "summary": r.summary_short,
            "category": r.category,
            "score": float(r.final_score or 0),
            "distance": float(r.distance),
        }
        for r in rows
    ]

    # 3. Build context and ask LLM
    context = "\n\n".join(
        f"[{i+1}] {a['title']}\n{a['summary'] or ''}\nSource: {a['url']}"
        for i, a in enumerate(articles)
    )

    prompt = f"""You are a personal news intelligence assistant.
Answer the user's question using ONLY the articles provided below.
Cite articles by number [1], [2], etc. Be concise and factual.
If the answer is not in the articles, say so clearly.

QUESTION: {payload.query}

ARTICLES:
{context}

ANSWER:"""

    async with httpx.AsyncClient(timeout=60) as client:
        llm_resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": LLM_MODEL, "prompt": prompt, "stream": False},
        )

    answer = llm_resp.json().get("response", "") if llm_resp.status_code == 200 else "(LLM unavailable)"

    return {
        "query": payload.query,
        "answer": answer,
        "articles": articles,
    }
