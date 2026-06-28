"""GitHub trending collector via unofficial scraping + GitHub search API."""
from __future__ import annotations

from datetime import datetime

import requests

from app.utils.logging import get_logger

log = get_logger("collector.github")

_SEARCH_URL = "https://api.github.com/search/repositories"
_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Helix/1.0",
}


def collect_github_trending(source: dict, days: int = 1) -> list[dict]:
    """
    Collect trending GitHub repos by topic using the GitHub Search API.
    No auth needed for public repos (60 req/hour unauthenticated).
    """
    topic = source.get("topic", "")
    lang  = source.get("language_filter", "")

    from datetime import timedelta
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    q = f"topic:{topic} stars:>10 pushed:>{since}" if topic else f"stars:>50 pushed:>{since}"
    if lang:
        q += f" language:{lang}"

    log.info("github_fetch", topic=topic, q=q)
    try:
        r = requests.get(
            _SEARCH_URL,
            params={"q": q, "sort": "stars", "order": "desc", "per_page": 30},
            headers=_HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        repos = r.json().get("items", [])
    except Exception as e:
        log.error("github_fetch_error", error=str(e))
        return []

    items = []
    for repo in repos:
        url = repo.get("html_url", "")
        pushed = repo.get("pushed_at")
        published_at = None
        if pushed:
            try:
                published_at = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
            except Exception:
                pass

        items.append({
            "url": url,
            "title": f"[GitHub] {repo.get('full_name', '')} — {repo.get('description', '')}",
            "snippet": repo.get("description", "")[:400],
            "published_at": published_at,
            "raw_payload": {
                "stars": repo.get("stargazers_count"),
                "forks": repo.get("forks_count"),
                "language": repo.get("language"),
                "topics": repo.get("topics", []),
                "owner": repo.get("owner", {}).get("login"),
            },
        })

    log.info("github_done", count=len(items))
    return items
