from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Article, ArticleAI, Source
from app.db.session import get_db

router = APIRouter()

PROJECTS_PATH = Path(__import__("os").environ.get("RESEARCH_PROJECTS_PATH", "/app/config/research_projects.yaml"))


def _load_projects() -> list[dict[str, Any]]:
    candidates = [PROJECTS_PATH, Path(str(PROJECTS_PATH) + ".example")]
    for path in candidates:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return [item for item in data.get("projects", []) if isinstance(item, dict)]
    return []


def _normalize_project(project: dict[str, Any]) -> dict[str, Any]:
    slug = str(project.get("slug") or project.get("name") or "").strip().lower().replace(" ", "_")
    keywords = [str(k).strip() for k in project.get("keywords", []) if str(k).strip()]
    return {
        "slug": slug,
        "name": project.get("name") or slug,
        "keywords": keywords,
        "priority": int(project.get("priority", 2) or 2),
        "description": project.get("description"),
    }


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


@router.get("/")
async def list_projects():
    items = [_normalize_project(project) for project in _load_projects() if _normalize_project(project).get("slug")]
    return {
        "count": len(items),
        "items": items,
    }


@router.get("/{slug}/articles")
async def list_project_articles(slug: str, limit: int = Query(default=50, ge=1, le=200), db: AsyncSession = Depends(get_db)):
    projects = [_normalize_project(project) for project in _load_projects()]
    project = next((item for item in projects if item.get("slug") == slug), None)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    keywords = [k.lower() for k in project.get("keywords", [])]
    if not keywords:
        return {"project": project, "count": 0, "items": []}

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
                ArticleAI.entities,
                ArticleAI.final_score,
                Source.name.label("source_name"),
            )
            .outerjoin(ArticleAI, ArticleAI.article_id == Article.id)
            .outerjoin(Source, Source.id == Article.source_id)
            .order_by(desc(article_date))
            .limit(max(limit * 5, 100))
        )
    ).all()

    items = []
    for row in rows:
        text_blob = " ".join([
            (row.title or ""),
            (row.summary_short or ""),
            (row.category or ""),
            _entities_blob(row.entities),
        ]).lower()
        matched_keywords = [keyword for keyword in keywords if keyword in text_blob]
        if not matched_keywords:
            continue

        items.append(
            {
                "id": row.id,
                "title": row.title,
                "url": row.url,
                "source": row.source_name,
                "published_at": row.article_date.isoformat() if isinstance(row.article_date, datetime) else None,
                "summary_short": row.summary_short,
                "category": row.category,
                "final_score": float(row.final_score or 0),
                "matched_keywords": matched_keywords,
            }
        )
        if len(items) >= limit:
            break

    return {
        "project": project,
        "count": len(items),
        "items": items,
    }
