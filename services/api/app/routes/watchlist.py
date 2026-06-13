from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Article, ArticleAI, EntityMention, Source, WatchlistEntity
from app.db.session import get_db

router = APIRouter()

WATCHLIST_PATH = Path(__import__("os").environ.get("WATCHLIST_PATH", "/app/config/watchlist.yaml"))


def _load_watchlist() -> dict[str, Any]:
    candidates = [WATCHLIST_PATH, Path(str(WATCHLIST_PATH) + ".example")]
    for path in candidates:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                if "watchlist" in data and isinstance(data["watchlist"], dict):
                    data = data["watchlist"]
                return data
    return {"entities": []}


def _extract_entities(config: dict[str, Any]) -> list[dict[str, Any]]:
    entities = config.get("entities", [])
    if entities and isinstance(entities[0], str):
        return [{"name": item, "type": "unknown", "priority": 2} for item in entities]
    return [item for item in entities if isinstance(item, dict) and item.get("name")]


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


async def _seed_watchlist_if_empty(db: AsyncSession) -> list[WatchlistEntity]:
    rows = (
        await db.execute(
            select(WatchlistEntity).where(WatchlistEntity.enabled.is_(True)).order_by(desc(WatchlistEntity.priority), WatchlistEntity.name)
        )
    ).scalars().all()
    if rows:
        return list(rows)

    config = _load_watchlist()
    entities = _extract_entities(config)
    for item in entities:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        db.add(
            WatchlistEntity(
                name=name,
                entity_type=str(item.get("type", "unknown")),
                priority=int(item.get("priority", 2) or 2),
                enabled=True,
            )
        )
    if entities:
        await db.commit()

    rows = (
        await db.execute(
            select(WatchlistEntity).where(WatchlistEntity.enabled.is_(True)).order_by(desc(WatchlistEntity.priority), WatchlistEntity.name)
        )
    ).scalars().all()
    return list(rows)


@router.get("/")
async def get_watchlist(db: AsyncSession = Depends(get_db)):
    db_entities = await _seed_watchlist_if_empty(db)

    if db_entities:
        entities = [
            {
                "id": int(item.id),
                "name": item.name,
                "type": item.entity_type,
                "priority": int(item.priority or 2),
                "enabled": bool(item.enabled),
            }
            for item in db_entities
        ]
    else:
        config = _load_watchlist()
        entities = _extract_entities(config)
    return {
        "count": len(entities),
        "entities": entities,
    }


@router.get("/matches")
async def get_watchlist_matches(limit: int = Query(default=50, ge=1, le=200), db: AsyncSession = Depends(get_db)):
    db_entities = await _seed_watchlist_if_empty(db)

    if db_entities:
        entities = [{"name": item.name, "priority": int(item.priority or 2)} for item in db_entities]
    else:
        config = _load_watchlist()
        entities = _extract_entities(config)

    needles = [str(item.get("name", "")).lower() for item in entities if item.get("name")]

    if not needles:
        return {"count": 0, "items": []}

    article_date = func.coalesce(Article.published_at, Article.discovered_at, Article.extracted_at)
    rows = (
        await db.execute(
            select(
                Article.id,
                Article.title,
                Article.url,
                article_date.label("article_date"),
                ArticleAI.summary_short,
                ArticleAI.final_score,
                ArticleAI.entities,
                Source.name.label("source_name"),
            )
            .outerjoin(ArticleAI, ArticleAI.article_id == Article.id)
            .outerjoin(Source, Source.id == Article.source_id)
            .order_by(desc(article_date))
            .limit(max(limit * 5, 100))
        )
    ).all()

    matches = []
    entity_ids_by_name = {str(item.name).lower(): int(item.id) for item in db_entities} if db_entities else {}
    for row in rows:
        title = (row.title or "").lower()
        summary = (row.summary_short or "").lower()
        entities_blob = _entities_blob(row.entities)
        matched = [name for name in needles if name and (name in title or name in summary or name in entities_blob)]
        if not matched:
            continue
        matches.append(
            {
                "id": row.id,
                "title": row.title,
                "url": row.url,
                "source": row.source_name,
                "published_at": row.article_date.isoformat() if isinstance(row.article_date, datetime) else None,
                "summary_short": row.summary_short,
                "final_score": float(row.final_score or 0),
                "matched_entities": matched,
            }
        )
        for name in matched:
            entity_id = entity_ids_by_name.get(name)
            if entity_id is None:
                continue
            existing_link = (
                await db.execute(
                    select(EntityMention).where(
                        and_(
                            EntityMention.article_id == int(row.id),
                            EntityMention.watchlist_entity_id == entity_id,
                        )
                    )
                )
            ).scalar_one_or_none()
            if existing_link is None:
                db.add(
                    EntityMention(
                        article_id=int(row.id),
                        watchlist_entity_id=entity_id,
                        mention_count=1,
                        matched_context=(row.summary_short or row.title or "")[:400],
                    )
                )
        if len(matches) >= limit:
            break

    if matches:
        await db.commit()

    return {
        "count": len(matches),
        "items": matches,
    }
