"""Reddit collector via public RSS (no auth required)."""
from __future__ import annotations

from urllib.parse import quote

from app.collectors.rss import collect_rss
from app.utils.logging import get_logger

log = get_logger("collector.reddit")


def collect_reddit(source: dict) -> list[dict]:
    subreddit = source.get("subreddit", "")
    if not subreddit:
        log.warning("reddit_no_subreddit", source=source.get("name"))
        return []

    rss_url = f"https://www.reddit.com/r/{quote(subreddit, safe='')}/hot/.rss?limit=50"
    log.info("reddit_fetch", subreddit=subreddit)
    items = collect_rss({**source, "url": rss_url})

    # Add subreddit metadata to each item
    for item in items:
        item.setdefault("raw_payload", {})["subreddit"] = subreddit

    return items
