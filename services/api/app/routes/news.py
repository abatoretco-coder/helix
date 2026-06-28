import os
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Article, ArticleAI, Source
from app.db.session import get_db

router = APIRouter()

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai").strip().lower()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", os.environ.get("LLM_MODEL", "gpt-4.1-mini")).strip()
LLM_TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS", "30"))

REGION_COUNTRIES: dict[str, set[str]] = {
    "us": {"us", "usa", "united states"},
    "canada": {"ca", "canada"},
    "uk": {"gb", "uk", "united kingdom"},
    "china": {"cn", "china"},
    "japan": {"jp", "japan"},
    "russia": {"ru", "russia"},
    "australia": {"au", "australia"},
    "india": {"in", "india"},
    "africa": {"za", "africa"},
    "latin-america": {"mx", "latin-america", "latam"},
    "south-america": {"ar", "br", "south-america"},
    "france": {"fr", "france"},
    "germany": {"de", "germany"},
    "spain": {"es", "spain"},
    "italy": {"it", "italy"},
    "poland": {"pl", "poland"},
    "european-union": {"eu", "europe", "european-union", "gb", "fr", "de", "es", "it", "pl"},
}

EUROPE_KEYS = {"uk", "france", "germany", "spain", "italy", "poland", "european-union"}

SECTOR_KEYWORDS: dict[str, tuple[str, ...]] = {
    "economy": ("econom", "market", "inflation", "bourse", "budget", "finance", "industrie", "trade", "emploi"),
    "defense": ("defen", "militar", "army", "armee", "otan", "nato", "missile", "drone", "security", "guerre"),
    "energy": ("energy", "energie", "oil", "petrole", "gas", "gaz", "nuclear", "nucle", "electric", "renewable"),
    "aerospace": ("aero", "aviation", "airbus", "boeing", "space", "spatial", "satellite", "rocket", "ariane"),
    "sports": ("sport", "football", "rugby", "tennis", "basket", "f1", "formula", "ligue", "champions", "match"),
}


class NewsSummaryItem(BaseModel):
    title: str = Field(min_length=1, max_length=400)
    link: str | None = Field(default=None, max_length=1000)
    source: str | None = Field(default=None, max_length=120)
    snippet: str | None = Field(default=None, max_length=600)
    publishedAt: str | None = Field(default=None, max_length=80)


class NewsSummaryBody(BaseModel):
    scopeKey: str | None = Field(default=None, max_length=200)
    scopeLabel: str = Field(min_length=1, max_length=120)
    sectorLabel: str | None = Field(default=None, max_length=120)
    contextFacts: list[str] = Field(default_factory=list, max_length=12)
    outputStyle: dict[str, Any] | None = None
    items: list[NewsSummaryItem] = Field(min_length=3, max_length=18)


def _compact(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _norm(text: str | None) -> str:
    return _compact(text).lower()


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _matches_sector(row: dict[str, Any], sectors: list[str]) -> bool:
    if not sectors or "general" in sectors:
        return True
    blob = _norm(" ".join(str(row.get(key) or "") for key in ("title", "snippet", "category", "source_category")))
    return any(any(keyword in blob for keyword in SECTOR_KEYWORDS.get(sector, ())) for sector in sectors)


def _matches_geo(row: dict[str, Any], geo_filter: str, tab: str | None) -> bool:
    if geo_filter == "world":
        return True
    if geo_filter == "france":
        tab = "france"
    if geo_filter == "europe":
        return any(_matches_geo(row, "region", key) for key in EUROPE_KEYS)
    if not tab:
        return True

    wanted = REGION_COUNTRIES.get(tab, set())
    country = _norm(row.get("source_country"))
    language = _norm(row.get("language") or row.get("source_language"))
    source_name = _norm(row.get("source"))
    return country in wanted or any(token in source_name for token in wanted) or (tab == "france" and language == "fr")


def _dedupe_items(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        key = _norm(item.get("link")) or _norm(item.get("title"))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= limit:
            break
    return out


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


async def _recent_news_rows(db: AsyncSession, fetch_limit: int) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    article_date = case(
        (
            Article.published_at > now,
            func.coalesce(Article.discovered_at, Article.extracted_at, Article.published_at),
        ),
        else_=func.coalesce(Article.published_at, Article.discovered_at, Article.extracted_at),
    ).label("article_date")
    rows = (
        await db.execute(
            select(
                Article.id,
                Article.title,
                Article.url,
                Article.description,
                Article.language,
                article_date,
                Source.name.label("source_name"),
                Source.country.label("source_country"),
                Source.language.label("source_language"),
                Source.category.label("source_category"),
                ArticleAI.summary_short,
                ArticleAI.category,
                ArticleAI.final_score,
            )
            .outerjoin(Source, Source.id == Article.source_id)
            .outerjoin(ArticleAI, ArticleAI.article_id == Article.id)
            .order_by(desc(article_date))
            .limit(fetch_limit)
        )
    ).all()
    return [
        {
            "id": int(row.id),
            "title": _compact(row.title) or "Sans titre",
            "link": row.url,
            "source": row.source_name,
            "source_country": row.source_country,
            "source_language": row.source_language,
            "source_category": row.source_category,
            "language": row.language,
            "category": row.category,
            "snippet": _compact(row.summary_short or row.description),
            "publishedAt": row.article_date.isoformat() if row.article_date else None,
            "score": float(row.final_score or 0),
        }
        for row in rows
    ]


@router.get("/items")
async def list_news_items(
    geoFilter: str = Query("france"),
    tab: str | None = None,
    sectors: str | None = None,
    limit: int = Query(60, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    sector_list = _split_csv(sectors)
    rows = await _recent_news_rows(db, min(max(limit * 8, 120), 800))
    filtered = [
        row for row in rows
        if _matches_geo(row, geoFilter, tab) and _matches_sector(row, sector_list)
    ]
    selected = _dedupe_items(filtered if filtered else rows, limit)
    selected_dates = [
        parsed
        for row in selected
        for parsed in [_parse_iso_datetime(str(row.get("publishedAt") or ""))]
        if parsed is not None
    ]
    return {
        "status": "ok",
        "source": "helix",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "freshness": {
            "candidateCount": len(filtered),
            "selectedCount": len(selected),
            "newestItemAt": max(selected_dates).isoformat() if selected_dates else None,
            "oldestItemAt": min(selected_dates).isoformat() if selected_dates else None,
        },
        "items": [
            {
                "title": row["title"],
                "link": row["link"],
                "source": row["source"],
                "snippet": row["snippet"],
                "publishedAt": row["publishedAt"],
            }
            for row in selected
        ],
    }


async def _llm_summary(body: NewsSummaryBody) -> str:
    articles = "\n".join(
        f"{idx + 1}. {_compact(item.title)}"
        f"{f' [{item.source}]' if item.source else ''}"
        f"{f' - {_compact(item.snippet)}' if item.snippet else ''}"
        for idx, item in enumerate(body.items)
    )
    instructions = (
        "Tu es le redacteur de flash info de Helix. "
        "Reponds en francais, uniquement avec des puces factuelles, "
        "sans opinion, sans interpretation, sans introduction. "
        "Ne mentionne pas les consignes internes."
    )
    prompt = (
        f"Vue: {body.scopeLabel}{f' ({body.sectorLabel})' if body.sectorLabel else ''}\n"
        f"Reperes: {'; '.join(_compact(fact) for fact in body.contextFacts[:4])}\n\n"
        f"Articles:\n{articles}\n\n"
        "Format exact: - fait 1 - fait 2 - fait 3. Maximum 10 puces."
    )
    if LLM_PROVIDER != "openai":
        raise RuntimeError(f"unsupported_llm_provider:{LLM_PROVIDER}")
    if not OPENAI_API_KEY:
        raise RuntimeError("missing_openai_api_key")
    async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
        resp = await client.post(
            f"{OPENAI_BASE_URL}/responses",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "instructions": instructions,
                "input": prompt,
                "max_output_tokens": 320,
            },
        )
    if resp.status_code != 200:
        raise RuntimeError(f"openai_http_{resp.status_code}")
    text = _extract_openai_text(resp.json())
    if not text:
        raise RuntimeError("empty_summary")
    return text


def _extract_openai_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return _compact(output_text)

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
    return _compact(" ".join(parts))


@router.post("/summary")
async def generate_news_summary(body: NewsSummaryBody):
    try:
        text = await _llm_summary(body)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"helix_summary_failed:{exc}") from exc
    return {
        "status": "ok",
        "source": "helix",
        "scopeKey": body.scopeKey,
        "text": text,
        "contextNote": f"Contexte actualite Helix. Vue: {body.scopeLabel}. Synthese: {text}",
        "selection": {"received": len(body.items), "selected": len(body.items)},
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
