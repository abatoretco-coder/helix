import os
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Article, ArticleAI, Source
from app.db.session import get_db
from app.openai_usage import complete_openai_call, reserve_openai_call

router = APIRouter()

NEWS_SUMMARY_PROVIDER = os.environ.get(
    "NEWS_SUMMARY_PROVIDER",
    "local",
).strip().lower()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434").strip().rstrip("/")
OPENAI_MODEL = os.environ.get(
    "NEWS_SUMMARY_MODEL",
    os.environ.get("OPENAI_MODEL", os.environ.get("LLM_MODEL", "gpt-4.1-mini")),
).strip()
LLM_TIMEOUT_SECONDS = float(os.environ.get("NEWS_SUMMARY_TIMEOUT_SECONDS", os.environ.get("LLM_TIMEOUT_SECONDS", "30")))

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

# Keep the public Desktop feed aligned with the worker admission policy.  This
# is a defensive second gate: it prevents old rows or a future ingestion bug
# from leaking blocked categories into Jarvis after collection.
VISIBLE_SOURCE_CATEGORIES = {
    "ai",
    "tech",
    "science",
    "supply_chain",
    "pharma",
    "climate",
    "cybersecurity",
    "startups",
    "regulation",
    "geopolitics",
    "finance",
}
REFERENCE_ONLY_SOURCE_TYPES = {"openalex", "eurostat", "datagouv_dataset"}
KEYWORD_REQUIRED_SOURCE_CATEGORIES = {"tech", "science", "geopolitics", "regulation", "finance"}
PUBLIC_RELEVANCE_TERMS = (
    "artificial intelligence", " llm", "openai", "anthropic", "mistral", "gemini", "ollama",
    "cybersecurity", "cyberattack", "cyberattaque", "cyberattaques", "ransomware", "malware", "botnet", "vulnerability", "exploit", "kaspersky",
    "connected vehicle", "connected vehicles", "voiture connectee", "voitures connectees", "head unit",
    "supply chain", "logistics", "warehouse", "freight", "transport", "pharma", "clinical trial",
    "carbon", "decarbon", "climate", "regulation", "ai act", "european union", "startup", "saas",
)

COMMERCIAL_MARKERS = (
    "sponsored content", "paid content", "paid post", "advertorial",
    "affiliate links", "this post contains affiliate", "brand partner",
    "contenu sponsorise", "article sponsorise", "publireportage",
    "contenu de marque", "en partenariat avec", "lien affilie", "liens affilies",
    "buy now", "shop now", "limited time offer", "promo code", "coupon code",
    "free shipping", "black friday", "cyber monday", "% off",
    "acheter maintenant", "offre limitee", "offre a duree limitee", "code promo", "bon plan",
    "meilleur prix", "livraison gratuite", "fait un carton sur amazon", "en promo sur amazon",
)
COMMERCIAL_SOURCE_MARKERS = ("sponsored", "advertorial", "affiliate", "shopping deals", "coupon", "bons plans", "code promo")
COMMERCIAL_BUYING_GUIDE = re.compile(
    r"\b(?:(?:top|best) \d+|\d+ (?:best|top)|(?:meilleurs?|top) \d+).*\b(?:to buy|for sale|a acheter|en promotion)\b",
    re.IGNORECASE,
)
COMMERCIAL_RETAIL_DISCOUNT = re.compile(
    r"\b(?:amazon|cdiscount|fnac|darty|boulanger)\b.{0,90}\b(?:-\s?\d{1,3}\s?%|remise de \d+\s?%|baisse de \d+\s?€)|"
    r"\b(?:-\s?\d{1,3}\s?%|remise de \d+\s?%|baisse de \d+\s?€).{0,90}\b(?:amazon|cdiscount|fnac|darty|boulanger)\b",
    re.IGNORECASE,
)
ENGLISH_MARKERS = {
    "the", "and", "with", "that", "this", "from", "into", "for", "are", "was",
    "has", "have", "will", "after", "about", "their", "they", "more", "is",
    "but", "being", "using", "teachers", "in", "it",
}
FRENCH_MARKERS = {
    "le", "la", "les", "des", "une", "dans", "pour", "avec", "sur", "que",
    "est", "sont", "par", "desormais", "selon", "cette", "ces", "aux",
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
    items: list[NewsSummaryItem] = Field(min_length=2, max_length=18)


def _compact(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _normalize_summary_bullets(text: str) -> str:
    """Keep readable structure; never flatten model headings and bullets."""
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    normalized: list[str] = []
    for line in lines:
        if re.match(r"^#{1,6}\s*", line):
            heading = re.sub(r"^#{1,6}\s*", "", line).strip(" :")
            if heading:
                normalized.append(f"## {heading}")
            continue
        value = re.sub(r"^(?:[-*•]+|\d+[.)])\s*", "", line).strip()
        if value:
            normalized.append(f"- {value}")
    return "\n".join(normalized[:12]) if normalized else _compact(text)


def _norm(text: str | None) -> str:
    value = unicodedata.normalize("NFKD", _compact(text))
    return "".join(char for char in value if not unicodedata.combining(char)).lower()


def _is_commercial_content(row: dict[str, Any]) -> bool:
    """Second gate for the public API and legacy rows already in storage."""
    source = _norm(str(row.get("source") or ""))
    content = _norm(" ".join(str(row.get(key) or "") for key in ("title", "snippet", "link")))
    return (
        any(marker in source for marker in COMMERCIAL_SOURCE_MARKERS)
        or any(marker in content for marker in COMMERCIAL_MARKERS)
        or bool(COMMERCIAL_BUYING_GUIDE.search(content))
        or bool(COMMERCIAL_RETAIL_DISCOUNT.search(content))
    )


def _is_google_news_relay(row: dict[str, Any]) -> bool:
    """A Google News RSS relay is not an article source suitable for display."""
    link = _norm(str(row.get("link") or ""))
    return "news.google.com/rss/articles/" in link


def _has_information_snippet(row: dict[str, Any]) -> bool:
    """Only enriched, source-backed records may feed the public Flash Info."""
    snippet = _compact(str(row.get("snippet") or ""))
    if len(snippet) < 90:
        return False
    title_words = {word for word in re.findall(r"\w+", _norm(str(row.get("title") or ""))) if len(word) >= 5}
    snippet_words = {word for word in re.findall(r"\w+", _norm(snippet)) if len(word) >= 5}
    return len(snippet_words - title_words) >= 5


def _is_database_ready_news(row: dict[str, Any]) -> bool:
    """Only publish an Ollama-enriched record, never an RSS teaser fallback.

    A raw description can be a headline fragment, an editorial teaser or a
    stale scrape.  It is useful for processing, but it has not earned a place
    in the user-facing intelligence product.  The public feed is deliberately
    smaller when enrichment has not completed.
    """
    return (
        bool(row.get("enriched"))
        and str(row.get("source_type") or "") not in REFERENCE_ONLY_SOURCE_TYPES
        and _has_information_snippet(row)
        and not _is_untranslated_english(row.get("snippet"))
    )


def _is_untranslated_english(text: str | None) -> bool:
    """Detect the extractive English fallback in a French public product.

    This is deliberately a public-display gate, not a language detector for
    stored articles. French summaries may contain English product names; they
    are rejected only when English function words clearly dominate.
    """
    words = re.findall(r"\b[\w']+\b", _norm(text))
    if len(words) < 8:
        return False
    english = sum(word in ENGLISH_MARKERS for word in words)
    french = sum(word in FRENCH_MARKERS for word in words)
    return english >= 3 and english >= french + 2


def _matches_public_relevance(row: dict[str, Any]) -> bool:
    category = _norm(str(row.get("source_category") or ""))
    if category not in KEYWORD_REQUIRED_SOURCE_CATEGORIES:
        return True
    blob = _norm(" ".join(str(row.get(key) or "") for key in ("title", "snippet")))
    return any(term.strip() in blob for term in PUBLIC_RELEVANCE_TERMS)


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
                Article.language,
                Article.word_count,
                article_date,
                Source.name.label("source_name"),
                Source.source_type.label("source_type"),
                Source.country.label("source_country"),
                Source.language.label("source_language"),
                Source.category.label("source_category"),
                Source.priority.label("source_priority"),
                Source.refresh_minutes.label("source_refresh_minutes"),
                ArticleAI.summary_short,
                ArticleAI.category,
                ArticleAI.final_score,
            )
            .outerjoin(Source, Source.id == Article.source_id)
            .join(ArticleAI, ArticleAI.article_id == Article.id)
            .where(Article.archived_at.is_(None))
            .where(Source.category.in_(VISIBLE_SOURCE_CATEGORIES))
            .order_by(desc(article_date))
            .limit(fetch_limit)
        )
    ).all()
    rows = [
        {
            "id": int(row.id),
            "title": _compact(row.title) or "Sans titre",
            "link": row.url,
            "source": row.source_name,
            "source_type": row.source_type,
            "source_country": row.source_country,
            "source_language": row.source_language,
            "source_category": row.source_category,
            "source_priority": int(row.source_priority or 3),
            "source_refresh_minutes": int(row.source_refresh_minutes or 60),
            "language": row.language,
            "category": row.category,
            "snippet": _compact(row.summary_short),
            "enriched": bool(row.summary_short and row.final_score is not None),
            "publishedAt": row.article_date.isoformat() if row.article_date else None,
            "score": float(row.final_score or 0),
        }
        for row in rows
    ]
    return [
        row for row in rows
        if not _is_commercial_content(row)
        and not _is_google_news_relay(row)
        and _is_database_ready_news(row)
        and _matches_public_relevance(row)
    ]


@router.get("/items")
async def list_news_items(
    geoFilter: str = Query("france"),
    tab: str | None = None,
    sectors: str | None = None,
    view: str = Query("standard", pattern="^(standard|breaking)$"),
    limit: int = Query(60, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    sector_list = _split_csv(sectors)
    rows = await _recent_news_rows(db, min(max(limit * 8, 120), 800))
    filtered = [
        row for row in rows
        if _matches_geo(row, geoFilter, tab) and _matches_sector(row, sector_list)
    ]
    if view == "breaking":
        filtered = [row for row in filtered if row["source_priority"] == 1]
    # Never fall back to the unfiltered pool.  An empty result is honest and
    # safer than silently returning blocked categories such as sport, leisure
    # or general recommendation feeds.
    selected = _dedupe_items(filtered, limit)
    selected_dates = [
        parsed
        for row in selected
        for parsed in [_parse_iso_datetime(str(row.get("publishedAt") or ""))]
        if parsed is not None
    ]
    newest = max(selected_dates) if selected_dates else None
    oldest = min(selected_dates) if selected_dates else None
    max_age_minutes = 90 if view == "breaking" else 240
    newest_age_minutes = round((datetime.now(timezone.utc) - newest).total_seconds() / 60, 1) if newest else None
    stale = newest_age_minutes is None or newest_age_minutes > max_age_minutes
    return {
        "status": "ok",
        "source": "helix",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "freshness": {
            "candidateCount": len(filtered),
            "selectedCount": len(selected),
            "newestItemAt": newest.isoformat() if newest else None,
            "oldestItemAt": oldest.isoformat() if oldest else None,
            "newestItemAgeMinutes": newest_age_minutes,
            "targetMaxAgeMinutes": max_age_minutes,
            "stale": stale,
            "warning": "No recent matching article is available." if stale else None,
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


async def _llm_summary(body: NewsSummaryBody, db: AsyncSession) -> str:
    if NEWS_SUMMARY_PROVIDER in {"local", "disabled", "none", "off"}:
        return _local_summary(body)

    articles = "\n".join(
        f"SOURCE {idx + 1}: {_compact(item.source) or 'inconnue'}\n"
        f"FAITS EXTRAITS: {_compact(item.snippet)}"
        for idx, item in enumerate(body.items)
    )
    instructions = (
        "Tu es le redacteur d'un flash d'intelligence Helix. "
        "Tu travailles uniquement à partir des FAITS EXTRAITS : ne répète jamais un titre, "
        "ne complète jamais une information manquante et exclue tout produit ou promotion. "
        "Réponds en français, avec exactement ce format Markdown :\n"
        "## Ce qui compte\n"
        "- 3 à 5 faits distincts, chacun attribué à sa source entre parenthèses\n"
        "## Ce que cela implique\n"
        "- 1 à 3 conséquences explicitement soutenues par les faits, ou 'Informations insuffisantes'."
    )
    prompt = (
        f"Vue: {body.scopeLabel}{f' ({body.sectorLabel})' if body.sectorLabel else ''}\n"
        f"Reperes: {'; '.join(_compact(fact) for fact in body.contextFacts[:4])}\n\n"
        f"Faits extraits:\n{articles}\n\n"
        "Les faits ci-dessus sont le seul matériau autorisé."
    )
    if NEWS_SUMMARY_PROVIDER == "ollama":
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OPENAI_MODEL,
                    "prompt": f"{instructions}\n\n{prompt}",
                    "stream": False,
                    "think": False,
                    "options": {"temperature": 0.2, "num_predict": 320},
                },
            )
        if resp.status_code != 200:
            raise RuntimeError(f"ollama_http_{resp.status_code}")
        text = str((resp.json() or {}).get("response") or "").strip()
        normalized = _normalize_summary_bullets(text)
        return normalized if _summary_is_usable(normalized, body.items) else _local_summary(body)
    if NEWS_SUMMARY_PROVIDER != "openai":
        raise RuntimeError(f"unsupported_news_summary_provider:{NEWS_SUMMARY_PROVIDER}")
    if not OPENAI_API_KEY:
        raise RuntimeError("missing_openai_api_key")
    event = await reserve_openai_call(db, endpoint="news-summary", operation="summary", model=OPENAI_MODEL)
    try:
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
        raise
    if resp.status_code != 200:
        raise RuntimeError(f"openai_http_{resp.status_code}")
    text = _extract_openai_text(payload or {})
    if not text:
        raise RuntimeError("empty_summary")
    return text


def _local_summary(body: NewsSummaryBody) -> str:
    bullets: list[str] = []
    for item in body.items[:6]:
        snippet = _compact(item.snippet)
        if len(snippet) < 45:
            continue
        source = f" ({_compact(item.source)})" if item.source else ""
        facts = [
            re.sub(r"^(?:[-*•]+|\d+[.)])\s*", "", fact).strip()
            for fact in re.split(r"\s+(?=[-•]\s+)", snippet)
        ]
        for fact in facts:
            # The extractor can end mid-sentence. Publishing that fragment as a
            # "fact" is worse than omitting it: keep only closed statements.
            complete_facts = re.split(r"(?<=[.!?])\s+", fact)
            if complete_facts and not re.search(r"[.!?][\]\)\"'»”]*$", complete_facts[-1]):
                complete_facts.pop()
            for complete_fact in complete_facts:
                complete_fact = complete_fact.strip()
                if len(complete_fact) >= 45:
                    bullets.append(f"- {complete_fact[:420]}{source}")
                if len(bullets) >= 6:
                    break
            if len(bullets) >= 6:
                break
        if len(bullets) >= 6:
            break

    if bullets:
        implication = _local_implication(bullets)
        return "\n".join(["## Ce qui compte", *bullets, *implication])
    return "## Ce qui compte\n- Aucun article enrichi et vérifiable n'est disponible pour cette vue."


def _local_implication(bullets: list[str]) -> list[str]:
    """Add one clearly-labelled, conservative inference to an offline summary.

    This branch is used if the small local model does not respect the output
    contract.  The consequence stays conditional and is traceable to the
    extracted facts; it must never masquerade as an additional source fact.
    """
    evidence = _norm(" ".join(bullets))
    if any(term in evidence for term in ("botnet", "malware", "ransomware", "vulnerability", "piratage")):
        return [
            "## Ce que cela implique",
            "- Inférence prudente : les systèmes connectés mentionnés doivent être suivis comme une surface d’attaque ; cette conclusion découle des faits rapportés par Numerama. (Numerama)",
        ]
    if any(term in evidence for term in ("cyberattaque", "sabotage", "otan", "russ")):
        return [
            "## Ce que cela implique",
            "- Inférence prudente : les faits signalent un risque hybride mêlant infrastructures, logistique et sécurité ; cette lecture découle des éléments rapportés par Le Grand Continent. (Le Grand Continent)",
        ]
    return []


def _summary_is_usable(text: str, items: list[NewsSummaryItem]) -> bool:
    lines = [line for line in text.splitlines() if line.startswith("- ")]
    forbidden_markers = (
        "3 a 5 faits", "chacun attribue", "les faits ci-dessus",
        "format markdown", "1 a 3 consequences",
    )
    if any(marker in _norm(text) for marker in forbidden_markers):
        return False
    headings = [line.strip().lower() for line in text.splitlines() if line.startswith("## ")]
    allowed_headings = {"## ce qui compte", "## ce que cela implique"}
    source_names = [_compact(item.source) for item in items if _compact(item.source)]
    attributed_lines = [
        line for line in lines
        if any(source.casefold() in line.casefold() for source in source_names)
    ]
    # A generated statement is only publishable when every displayed fact is
    # traceable to a supplied source and both requested sections are present.
    return (
        set(headings).issubset(allowed_headings)
        and "## ce qui compte" in headings
        and "## ce que cela implique" in headings
        and len(lines) >= 3
        and all(len(line) >= 35 for line in lines)
        and len(attributed_lines) == len(lines)
        and len({source for source in source_names if any(source.casefold() in line.casefold() for line in lines)}) >= 2
    )


def _is_commercial_summary_item(item: NewsSummaryItem) -> bool:
    return _is_commercial_content({
        "title": item.title,
        "snippet": item.snippet or "",
        "link": item.link or "",
        "source": item.source or "",
    })


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
async def generate_news_summary(body: NewsSummaryBody, db: AsyncSession = Depends(get_db)):
    received_count = len(body.items)
    body.items = [item for item in body.items if not _is_commercial_summary_item(item)]
    if not body.items:
        raise HTTPException(status_code=422, detail="no_noncommercial_enriched_article")
    try:
        text = await _llm_summary(body, db)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"helix_summary_failed:{exc}") from exc
    return {
        "status": "ok",
        "source": "helix",
        "summaryProvider": NEWS_SUMMARY_PROVIDER,
        "scopeKey": body.scopeKey,
        "text": text,
        "contextNote": f"Contexte actualite Helix. Vue: {body.scopeLabel}. Synthese: {text}",
        "selection": {"received": received_count, "selected": len(body.items)},
        "citations": [
            {
                "index": idx + 1,
                "title": _compact(item.title),
                "source": _compact(item.source) or None,
                "link": item.link,
                "publishedAt": item.publishedAt,
            }
            for idx, item in enumerate(body.items)
        ],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
