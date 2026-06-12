"""YouTube channel collector via YouTube XML feed (no API key needed)."""
from __future__ import annotations

from app.collectors.rss import collect_rss
from app.utils.logging import get_logger

log = get_logger("collector.youtube")


def collect_youtube(source: dict) -> list[dict]:
    channel_id = source.get("channel_id", "")
    if not channel_id:
        log.warning("youtube_no_channel_id", source=source.get("name"))
        return []

    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    log.info("youtube_fetch", channel_id=channel_id)
    items = collect_rss({**source, "url": rss_url})

    for item in items:
        item.setdefault("raw_payload", {})["platform"] = "youtube"
        item.setdefault("raw_payload", {})["channel_id"] = channel_id

    return items
