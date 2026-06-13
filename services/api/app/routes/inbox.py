from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Article, ArticleAI, ArticleUserState, Source, WatchlistEntity
from app.db.session import get_db

router = APIRouter()

WATCHLIST_PATH = Path(__import__("os").environ.get("WATCHLIST_PATH", "/app/config/watchlist.yaml"))
USER_PROFILE_PATH = Path(__import__("os").environ.get("USER_PROFILE_PATH", "/app/config/user_profile.yaml"))


def _load_watchlist_needles() -> list[str]:
    candidates = [WATCHLIST_PATH, Path(str(WATCHLIST_PATH) + ".example")]
    for path in candidates:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                watchlist = data.get("watchlist", data)
                entities = watchlist.get("entities", []) if isinstance(watchlist, dict) else []
                if entities and isinstance(entities[0], dict):
                    return [str(item.get("name", "")).lower() for item in entities if item.get("name")]
                return [str(item).lower() for item in entities if str(item).strip()]
    return []


def _load_boost_entities() -> list[str]:
    candidates = [USER_PROFILE_PATH, Path(str(USER_PROFILE_PATH) + ".example")]
    for path in candidates:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                profile = data.get("profile", data)
                entities = profile.get("boost_entities", []) if isinstance(profile, dict) else []
                return [str(item).lower() for item in entities if str(item).strip()]
    return []


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
async def inbox(
    limit: int = Query(default=50, ge=1, le=200),
    category: str | None = None,
    min_score: float | None = None,
    hide_read: bool = False,
    hide_hidden: bool = True,
    profile_id: str = Query(default="default"),
    mode: str = Query(default="top", pattern="^(top|recent|long_reads|watchlist)$"),
    db: AsyncSession = Depends(get_db),
):
    article_date = func.coalesce(Article.published_at, Article.discovered_at, Article.extracted_at).label("article_date")

    q = (
        select(
            Article.id,
            Article.title,
            Article.url,
            article_date,
            Article.word_count,
            ArticleAI.summary_short,
            ArticleAI.category,
            ArticleAI.final_score,
            ArticleAI.entities,
            ArticleUserState.is_read,
            ArticleUserState.is_saved,
            ArticleUserState.is_hidden,
            Source.name.label("source_name"),
        )
        .outerjoin(ArticleAI, ArticleAI.article_id == Article.id)
        .outerjoin(
            ArticleUserState,
            and_(
                ArticleUserState.article_id == Article.id,
                ArticleUserState.profile_id == profile_id,
            ),
        )
        .outerjoin(Source, Source.id == Article.source_id)
    )

    if category:
        q = q.where(ArticleAI.category == category)
    if min_score is not None:
        q = q.where(ArticleAI.final_score >= min_score)
    if hide_read:
        q = q.where(or_(ArticleUserState.is_read.is_(False), ArticleUserState.is_read.is_(None)))
    if hide_hidden:
        q = q.where(or_(ArticleUserState.is_hidden.is_(False), ArticleUserState.is_hidden.is_(None)))

    if mode == "top":
        q = q.order_by(desc(ArticleAI.final_score), desc(article_date))
    elif mode == "recent":
        q = q.order_by(desc(article_date))
    elif mode == "long_reads":
        q = q.where(Article.word_count.is_not(None)).where(Article.word_count > 1200).order_by(desc(Article.word_count), desc(article_date))
    else:
        q = q.order_by(desc(article_date))

    rows = (await db.execute(q.limit(max(limit * 5, 100)))).all()

    needles = []
    if mode == "watchlist":
        db_entities = (
            await db.execute(select(WatchlistEntity).where(WatchlistEntity.enabled.is_(True)))
        ).scalars().all()
        db_needles = [str(item.name).lower() for item in db_entities]
        needles = sorted(set(db_needles + _load_watchlist_needles() + _load_boost_entities()))
    items = []
    for row in rows:
        if mode == "watchlist":
            blob = " ".join([(row.title or ""), (row.summary_short or ""), _entities_blob(row.entities)]).lower()
            matched_watchlist = [needle for needle in needles if needle and needle in blob]
            if not matched_watchlist:
                continue
        else:
            matched_watchlist = []

        items.append(
            {
                "id": row.id,
                "title": row.title,
                "url": row.url,
                "source": row.source_name,
                "published_at": row.article_date.isoformat() if row.article_date else None,
                "summary_short": row.summary_short,
                "category": row.category,
                "final_score": float(row.final_score or 0),
                "word_count": row.word_count,
                "is_read": bool(row.is_read) if row.is_read is not None else False,
                "is_saved": bool(row.is_saved) if row.is_saved is not None else False,
                "is_hidden": bool(row.is_hidden) if row.is_hidden is not None else False,
                "matched_watchlist": matched_watchlist,
            }
        )
        if len(items) >= limit:
            break

    return {
        "mode": mode,
        "hide_read": hide_read,
        "hide_hidden": hide_hidden,
        "profile_id": profile_id,
        "read_state_supported": True,
        "count": len(items),
        "items": items,
    }
