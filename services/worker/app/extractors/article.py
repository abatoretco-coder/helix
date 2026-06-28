"""
Article extractor — orchestrates the chain defined in the architecture doc:

  1. RSS content (if full text already in feed)
  2. morss  — https://github.com/pictuga/morss  (enrich thin RSS via HTTP proxy)
  3. trafilatura — https://github.com/adbar/trafilatura
  4. news-please — https://github.com/fhamborg/news-please
  5. newspaper4k — fork of newspaper3k
  6. Playwright — last resort, JS-rendered pages only

Returns an ExtractedArticle or None on full failure.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import requests
from app.utils.logging import get_logger

log = get_logger("extractor")

MORSS_URL = os.environ.get("MORSS_URL", "http://morss:8080")
ENABLE_MORSS_FOR_ALL = os.environ.get("ENABLE_MORSS_FOR_ALL", "false").lower() == "true"
_SESSION = requests.Session()
_SESSION.headers["User-Agent"] = "Helix/1.0 (+https://github.com)"
_SESSION.headers["Accept-Language"] = "en,fr;q=0.9"


@dataclass
class ExtractedArticle:
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    text_content: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[str] = None
    language: Optional[str] = None
    image_url: Optional[str] = None
    raw_html: Optional[str] = None
    extractor_used: Optional[str] = None
    word_count: int = 0


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — RSS content
# ─────────────────────────────────────────────────────────────────────────────

def try_rss_content(raw_payload: dict) -> Optional[str]:
    """If the RSS feed already included the full article text, return it."""
    content = raw_payload.get("content") or raw_payload.get("summary", "")
    if isinstance(content, list) and content:
        content = content[0].get("value", "")
    if isinstance(content, str) and len(content) > 800:
        return content
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — morss (https://github.com/pictuga/morss)
# Morss proxies RSS feeds and fills in full article content.
# We use it to pre-fetch enriched HTML when the source has thin RSS.
# ─────────────────────────────────────────────────────────────────────────────

def try_morss(url: str) -> Optional[str]:
    """
    Use morss as an HTTP proxy to fetch full article HTML.
    Morss URL format:  http://morss:8080/<article_url>
    Returns raw HTML string or None.
    """
    morss_endpoint = f"{MORSS_URL}/{url}"
    try:
        resp = _SESSION.get(morss_endpoint, timeout=15)
        if resp.status_code == 200 and len(resp.text) > 500:
            return resp.text
    except Exception as exc:
        log.debug("morss_failed", url=url, error=str(exc))
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — trafilatura (https://github.com/adbar/trafilatura)
# ─────────────────────────────────────────────────────────────────────────────

def try_trafilatura(url: str, html: Optional[str] = None) -> Optional[ExtractedArticle]:
    """
    Extract with trafilatura. Can work from a pre-fetched HTML string
    (e.g., from morss) or fetch the URL itself.
    """
    try:
        import trafilatura
        from trafilatura.settings import use_config

        config = use_config()
        config.set("DEFAULT", "EXTRACTION_TIMEOUT", "20")

        if html is None:
            html = trafilatura.fetch_url(url)

        if not html:
            return None

        result = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
            output_format="json",
        )
        if not result:
            return None

        import json as _json
        data = _json.loads(result)

        text = data.get("text") or ""
        if len(text) < 200:
            return None

        return ExtractedArticle(
            url=url,
            title=data.get("title"),
            description=data.get("description"),
            text_content=text,
            author=data.get("author"),
            published_at=data.get("date"),
            language=data.get("language"),
            image_url=data.get("image"),
            raw_html=html,
            extractor_used="trafilatura",
            word_count=len(text.split()),
        )
    except Exception as exc:
        log.debug("trafilatura_failed", url=url, error=str(exc))
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — news-please (https://github.com/fhamborg/news-please)
# ─────────────────────────────────────────────────────────────────────────────

def try_newsplease(url: str) -> Optional[ExtractedArticle]:
    """
    Extract using news-please. It fetches and parses the article autonomously.
    news-please handles title, text, date, author, language, image.
    """
    try:
        from newsplease import NewsPlease

        article = NewsPlease.from_url(url, timeout=20)
        if not article:
            return None

        text = article.maintext or ""
        if len(text) < 200:
            return None

        published = None
        if article.date_publish:
            published = str(article.date_publish)
        elif article.date_modify:
            published = str(article.date_modify)

        return ExtractedArticle(
            url=url,
            title=article.title,
            description=article.description,
            text_content=text,
            author=article.authors[0] if article.authors else None,
            published_at=published,
            language=article.language,
            image_url=article.image_url,
            raw_html=None,
            extractor_used="news-please",
            word_count=len(text.split()),
        )
    except Exception as exc:
        log.debug("newsplease_failed", url=url, error=str(exc))
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — newspaper4k (fork of newspaper3k)
# ─────────────────────────────────────────────────────────────────────────────

def try_newspaper(url: str) -> Optional[ExtractedArticle]:
    try:
        import newspaper

        article = newspaper.Article(url, language="en", fetch_images=False)
        article.download()
        article.parse()
        article.nlp()

        text = article.text or ""
        if len(text) < 200:
            return None

        return ExtractedArticle(
            url=url,
            title=article.title,
            description=article.meta_description,
            text_content=text,
            author=article.authors[0] if article.authors else None,
            published_at=str(article.publish_date) if article.publish_date else None,
            language=article.meta_lang,
            image_url=article.top_image,
            raw_html=article.html,
            extractor_used="newspaper4k",
            word_count=len(text.split()),
        )
    except Exception as exc:
        log.debug("newspaper_failed", url=url, error=str(exc))
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Step 6 — Playwright (https://playwright.dev/python)
# Used only for JS-heavy pages when all other extractors fail.
# ─────────────────────────────────────────────────────────────────────────────

def try_playwright(url: str) -> Optional[ExtractedArticle]:
    """
    Render the page with a headless Chromium browser, then pass the HTML
    to trafilatura. Only triggered when all other methods fail.
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=30_000, wait_until="domcontentloaded")
            html = page.content()
            browser.close()

        if not html:
            return None

        result = try_trafilatura(url, html=html)
        if result:
            result.extractor_used = "playwright+trafilatura"
        return result

    except Exception as exc:
        log.debug("playwright_failed", url=url, error=str(exc))
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Main orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def extract_article(
    url: str,
    raw_payload: Optional[dict] = None,
    extraction_strategy: str = "article",
    use_playwright: bool = False,
) -> Optional[ExtractedArticle]:
    """
    Try each extractor in order. Returns first successful result.

    Strategies:
      rss           — use RSS content only (no HTTP fetch)
      rss_then_article — try RSS content first, then fall through
      morss         — use morss proxy first
      article       — full extraction chain (trafilatura → news-please → newspaper4k)
      reddit        — use RSS content (Reddit posts have full text in feed)
      github        — RSS content only
      youtube       — RSS content only (titles/descriptions)
    """
    raw_payload = raw_payload or {}

    # ── Shortcut strategies ──────────────────────────────────────────────────
    if extraction_strategy in ("rss", "reddit", "github", "youtube"):
        text = try_rss_content(raw_payload)
        return ExtractedArticle(
            url=url,
            title=raw_payload.get("title"),
            text_content=text or raw_payload.get("snippet", ""),
            extractor_used="rss_content",
            word_count=len((text or "").split()),
        )

    # ── rss_then_article: try RSS full text first ────────────────────────────
    if extraction_strategy == "rss_then_article":
        rss_text = try_rss_content(raw_payload)
        if rss_text:
            return ExtractedArticle(
                url=url,
                title=raw_payload.get("title"),
                text_content=rss_text,
                extractor_used="rss_content",
                word_count=len(rss_text.split()),
            )

    # ── morss pre-fetch (step 2) ─────────────────────────────────────────────
    morss_html = None
    use_morss = extraction_strategy in ("morss", "rss_then_morss") or ENABLE_MORSS_FOR_ALL
    if use_morss:
        morss_html = try_morss(url)

    # ── trafilatura (step 3) ─────────────────────────────────────────────────
    result = try_trafilatura(url, html=morss_html)
    if result and result.word_count >= 100:
        log.info("extracted", url=url, extractor=result.extractor_used, words=result.word_count)
        return result

    # ── news-please (step 4) ─────────────────────────────────────────────────
    result = try_newsplease(url)
    if result and result.word_count >= 100:
        log.info("extracted", url=url, extractor=result.extractor_used, words=result.word_count)
        return result

    # ── newspaper4k (step 5) ─────────────────────────────────────────────────
    result = try_newspaper(url)
    if result and result.word_count >= 100:
        log.info("extracted", url=url, extractor=result.extractor_used, words=result.word_count)
        return result

    # ── Playwright (step 6 — only if explicitly allowed) ─────────────────────
    if use_playwright:
        result = try_playwright(url)
        if result and result.word_count >= 100:
            log.info("extracted", url=url, extractor=result.extractor_used, words=result.word_count)
            return result

    log.warning("extraction_failed_all_methods", url=url)
    return None
