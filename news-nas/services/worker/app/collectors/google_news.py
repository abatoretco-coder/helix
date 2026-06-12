"""Google News RSS collector."""
from __future__ import annotations

from urllib.parse import quote_plus
from app.collectors.rss import collect_rss
from app.utils.logging import get_logger

log = get_logger("collector.google_news")

_BASE_FR = "https://news.google.com/rss/search?q={query}&hl=fr&gl=FR&ceid=FR:fr"
_BASE_EN = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
_BASE_GENERIC = "https://news.google.com/rss/search?q={query}&hl={lang}&gl={country}&ceid={country}:{lang_short}"


def collect_google_news(source: dict) -> list[dict]:
    query = source.get("query", "")
    lang  = source.get("language", "en")
    country = (source.get("country") or "US").upper()

    if lang == "fr":
        url = _BASE_FR.format(query=quote_plus(query))
    elif lang == "en":
        url = _BASE_EN.format(query=quote_plus(query))
    else:
        url = _BASE_GENERIC.format(
            query=quote_plus(query),
            lang=lang,
            country=country,
            lang_short=lang.split("-")[0],
        )

    log.info("gnews_fetch", query=query, url=url)
    return collect_rss({**source, "url": url})
