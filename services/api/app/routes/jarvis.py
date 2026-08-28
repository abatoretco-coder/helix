import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Article, ArticleAI, Briefing, Source
from app.openai_usage import complete_openai_call, reserve_openai_call

router = APIRouter()

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai").strip().lower()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434").strip().rstrip("/")
EMBED_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")).strip()
OLLAMA_EMBED_MODEL = os.environ.get("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text").strip()
EMBED_DIMENSIONS = int(os.environ.get("EMBEDDING_DIMENSIONS", "768"))
LLM_MODEL = os.environ.get("OPENAI_MODEL", os.environ.get("LLM_MODEL", "gpt-4.1-mini")).strip()
LLM_TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS", "30"))
JARVIS_OUTPUT_TOKENS = int(os.environ.get("JARVIS_OUTPUT_TOKENS", "420"))
PROMPTS_PATH = Path(os.environ.get("PROMPTS_PATH", "/app/config/llm_prompts.yaml"))
WATCHLIST_PATH = Path(os.environ.get("WATCHLIST_PATH", "/app/config/watchlist.yaml"))
PROJECTS_PATH = Path(os.environ.get("RESEARCH_PROJECTS_PATH", "/app/config/research_projects.yaml"))
SUSPENDED_SOURCE_CATEGORIES = {"countries", "recommended", "general", "travel"}


class DashboardSummaryItem(BaseModel):
    title: str = Field(min_length=1, max_length=400)
    summary: str = Field(min_length=1, max_length=2000)
    source: str | None = Field(default=None, max_length=120)
    url: str | None = Field(default=None, max_length=1000)
    score: float | None = Field(default=None, ge=0, le=1)
    category: str | None = Field(default=None, max_length=100)


class JarvisQuery(BaseModel):
    query: str
    mode: str = Field(default="search", pattern="^(briefing|search|watchlist|project|dashboard)$")
    language: str = "fr"
    max_sources: int = Field(default=8, ge=1, le=25)
    include_links: bool = True
    # Legacy compatibility
    date_range: str = "today"
    categories: list[str] = []
    limit: int | None = None
    dashboard_items: list[DashboardSummaryItem] = Field(default_factory=list, max_length=25)


def _load_config(path: Path, key: str) -> list[dict[str, Any]]:
    candidates = [path, Path(str(path) + ".example")]
    for candidate in candidates:
        if candidate.exists():
            with candidate.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return [row for row in data.get(key, []) if isinstance(row, dict)]
    return []


def _prompt_template(key: str, fallback: str) -> str:
    if not PROMPTS_PATH.exists():
        return fallback
    try:
        with PROMPTS_PATH.open("r", encoding="utf-8") as handle:
            prompts = yaml.safe_load(handle) or {}
        value = prompts.get(key)
        return str(value).strip() if value else fallback
    except Exception:
        return fallback


def _text_contains_any(text_blob: str, needles: list[str]) -> list[str]:
    return [needle for needle in needles if needle and needle in text_blob]


async def _embedding_search(db: AsyncSession, query: str, limit: int) -> list[dict[str, Any]]:
    if LLM_PROVIDER == "ollama":
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
                resp = await client.post(
                    f"{OLLAMA_BASE_URL}/api/embed",
                    json={"model": OLLAMA_EMBED_MODEL, "input": query[:4000]},
                )
            embeddings = (resp.json() or {}).get("embeddings") or []
            query_embedding = embeddings[0] if resp.status_code == 200 and embeddings else None
        except Exception as exc:
            raise HTTPException(502, "Embedding service unavailable") from exc
    elif LLM_PROVIDER == "openai" and OPENAI_API_KEY:
        event = await reserve_openai_call(db, endpoint="jarvis", operation="embedding", model=EMBED_MODEL)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{OPENAI_BASE_URL}/embeddings",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={"model": EMBED_MODEL, "input": query, "dimensions": EMBED_DIMENSIONS},
                )
            payload = resp.json() if resp.content else None
            await complete_openai_call(
                db,
                event,
                succeeded=resp.status_code == 200,
                payload=payload,
                error_message=None if resp.status_code == 200 else f"openai_http_{resp.status_code}",
            )
        except Exception as exc:
            await complete_openai_call(db, event, succeeded=False, error_message=str(exc))
            raise HTTPException(502, "Embedding service unavailable") from exc
        data = (payload or {}).get("data") or []
        query_embedding = data[0].get("embedding") if resp.status_code == 200 and data else None
    else:
        return []
    if not isinstance(query_embedding, list) or len(query_embedding) != EMBED_DIMENSIONS:
        return []

    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    sql = text(
        """
        SELECT a.id, a.title, a.url, a.published_at, s.name AS source_name,
               ai.summary_short, ai.category, ai.final_score,
               ai.embedding <=> :emb AS distance
        FROM article_ai ai
        JOIN articles a ON a.id = ai.article_id
        LEFT JOIN sources s ON s.id = a.source_id
        WHERE ai.embedding IS NOT NULL
          AND a.archived_at IS NULL
          AND (s.category IS NULL OR s.category NOT IN ('countries', 'recommended', 'general', 'travel'))
        ORDER BY ai.embedding <=> :emb
        LIMIT :limit
        """
    )
    result = await db.execute(sql, {"emb": embedding_str, "limit": limit})
    rows = result.fetchall()
    return [
        {
            "id": row.id,
            "title": row.title,
            "url": row.url,
            "source": row.source_name,
            "published_at": row.published_at.isoformat() if row.published_at else None,
            "summary": row.summary_short,
            "score": float(row.final_score or 0),
            "category": row.category,
        }
        for row in rows
    ]


async def _recent_articles(db: AsyncSession, limit: int) -> list[dict[str, Any]]:
    article_date = func.coalesce(Article.published_at, Article.discovered_at, Article.extracted_at).label("article_date")
    rows = (
        await db.execute(
            select(
                Article.id,
                Article.title,
                Article.url,
                article_date,
                Source.name.label("source_name"),
                ArticleAI.summary_short,
                ArticleAI.category,
                ArticleAI.final_score,
                ArticleAI.entities,
            )
            .outerjoin(ArticleAI, ArticleAI.article_id == Article.id)
            .outerjoin(Source, Source.id == Article.source_id)
            .where(Article.archived_at.is_(None))
            .where((Source.category.is_(None)) | (~Source.category.in_(SUSPENDED_SOURCE_CATEGORIES)))
            .order_by(desc(article_date))
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": row.id,
            "title": row.title,
            "url": row.url,
            "source": row.source_name,
            "published_at": row.article_date.isoformat() if row.article_date else None,
            "summary": row.summary_short,
            "score": float(row.final_score or 0),
            "category": row.category,
            "entities": row.entities,
        }
        for row in rows
    ]


def _entities_blob(entities: Any) -> str:
    if not entities:
        return ""
    if isinstance(entities, dict):
        values: list[str] = []
        for value in entities.values():
            if isinstance(value, list):
                values.extend(str(v) for v in value)
            else:
                values.append(str(value))
        return " ".join(values).lower()
    return str(entities).lower()


def _extract_openai_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    parts: list[str] = []
    for item in payload.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text)
    return " ".join(parts).strip()


async def _sources_for_mode(db: AsyncSession, payload: JarvisQuery, limit: int) -> list[dict[str, Any]]:
    if payload.mode == "dashboard":
        return [
            {
                "title": item.title,
                "url": item.url,
                "source": item.source or "dashboard",
                "published_at": None,
                "score": item.score if item.score is not None else 0.7,
                "summary": item.summary,
                "category": item.category,
            }
            for item in payload.dashboard_items[:limit]
        ]
    if payload.mode == "briefing":
        latest = (
            await db.execute(
                select(Briefing).where(Briefing.period == "daily").order_by(desc(Briefing.generated_at)).limit(1)
            )
        ).scalar_one_or_none()
        if not latest:
            return []
        return [
            {
                "title": f"Daily briefing {latest.period_date.isoformat() if latest.period_date else 'unknown'}",
                "url": None,
                "source": "helix_briefing",
                "published_at": latest.generated_at.isoformat() if latest.generated_at else None,
                "score": 1.0,
                "summary": latest.content or "No briefing content.",
            }
        ]

    if payload.mode == "search":
        try:
            matches = await _embedding_search(db, payload.query, limit)
            if matches:
                return matches
        except HTTPException:
            raise
        except Exception:
            pass

    rows = await _recent_articles(db, max(limit * 6, 120))
    if payload.mode == "watchlist":
        watchlist = _load_config(WATCHLIST_PATH, "entities")
        needles = [str(item.get("name", "")).lower() for item in watchlist if item.get("name")]
        filtered = []
        for row in rows:
            blob = " ".join([(row.get("title") or ""), (row.get("summary") or ""), _entities_blob(row.get("entities"))]).lower()
            if _text_contains_any(blob, needles):
                filtered.append(row)
            if len(filtered) >= limit:
                break
        return filtered

    if payload.mode == "project":
        projects = _load_config(PROJECTS_PATH, "projects")
        keywords: list[str] = []
        for project in projects:
            project_keywords = [str(item).lower() for item in project.get("keywords", [])]
            if any(token in payload.query.lower() for token in [str(project.get("slug", "")).lower(), str(project.get("name", "")).lower()]):
                keywords = project_keywords
                break
        if not keywords and projects:
            keywords = [str(item).lower() for item in projects[0].get("keywords", [])]
        filtered = []
        for row in rows:
            blob = " ".join([(row.get("title") or ""), (row.get("summary") or ""), str(row.get("category") or ""), _entities_blob(row.get("entities"))]).lower()
            if _text_contains_any(blob, keywords):
                filtered.append(row)
            if len(filtered) >= limit:
                break
        return filtered

    query_tokens = [token for token in payload.query.lower().split() if len(token) > 2]
    filtered = []
    for row in rows:
        blob = " ".join([(row.get("title") or ""), (row.get("summary") or ""), str(row.get("category") or "")]).lower()
        if any(token in blob for token in query_tokens):
            filtered.append(row)
        if len(filtered) >= limit:
            break
    return filtered if filtered else rows[:limit]


@router.post("/query")
async def jarvis_query(payload: JarvisQuery, db: AsyncSession = Depends(get_db)):
    effective_limit = payload.max_sources
    if payload.limit is not None:
        effective_limit = max(1, min(int(payload.limit), 25))

    sources = await _sources_for_mode(db, payload, effective_limit)
    context = "\n\n".join(
        f"[{i+1}] {item.get('title') or 'Untitled'}\n{str(item.get('summary') or '')[:1200]}\nSource: {item.get('source') or 'unknown'}\nURL: {item.get('url') or 'n/a'}"
        for i, item in enumerate(sources)
    )

    prompt_key = "jarvis_dashboard" if payload.mode == "dashboard" else "jarvis_answer"
    prompt = f"""{_prompt_template(prompt_key, 'Answer only from the supplied sources.')}

Language: {payload.language}
Mode: {payload.mode}
QUESTION: {payload.query}

SOURCES:
{context or 'No sources were selected.'}"""

    answer = "No data available for this query."
    try:
        if LLM_PROVIDER == "ollama":
            async with httpx.AsyncClient(timeout=60) as client:
                llm_resp = await client.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": LLM_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "think": False,
                        "options": {"temperature": 0.2, "num_predict": JARVIS_OUTPUT_TOKENS},
                    },
                )
            if llm_resp.status_code == 200:
                answer = str((llm_resp.json() or {}).get("response") or "").strip() or answer
        elif LLM_PROVIDER == "openai" and OPENAI_API_KEY:
            event = await reserve_openai_call(db, endpoint="jarvis", operation="answer", model=LLM_MODEL)
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    llm_resp = await client.post(
                        f"{OPENAI_BASE_URL}/responses",
                        headers={
                            "Authorization": f"Bearer {OPENAI_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={"model": LLM_MODEL, "input": prompt, "max_output_tokens": JARVIS_OUTPUT_TOKENS},
                    )
                llm_payload = llm_resp.json() if llm_resp.content else None
                await complete_openai_call(
                    db,
                    event,
                    succeeded=llm_resp.status_code == 200,
                    payload=llm_payload,
                    error_message=None if llm_resp.status_code == 200 else f"openai_http_{llm_resp.status_code}",
                )
            except Exception as exc:
                await complete_openai_call(db, event, succeeded=False, error_message=str(exc))
                raise
            if llm_resp.status_code == 200:
                answer = _extract_openai_text(llm_payload or {}) or answer
        else:
            answer = "LLM unavailable; returning structured sources only."
    except Exception:
        answer = "LLM unavailable; returning structured sources only."

    confidence = 0.0
    if sources:
        confidence = sum(float(item.get("score") or 0.0) for item in sources) / max(len(sources), 1)
        confidence = max(0.0, min(confidence, 1.0))

    source_items = [
        {
            "title": item.get("title"),
            "url": item.get("url") if payload.include_links else None,
            "source": item.get("source"),
            "published_at": item.get("published_at"),
            "score": float(item.get("score") or 0.0),
        }
        for item in sources[:effective_limit]
    ]

    return {
        "answer": answer,
        "mode": payload.mode,
        "provider": LLM_PROVIDER,
        "source_count": len(sources),
        "sources": source_items,
        "confidence": round(confidence, 3),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        # Legacy compatibility fields
        "query": payload.query,
        "articles": source_items,
    }
