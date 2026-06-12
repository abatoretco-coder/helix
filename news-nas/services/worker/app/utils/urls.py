"""URL normalization — removes tracking params, normalizes format."""
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

_TRACKING_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "utm_reader", "utm_name",
    "fbclid", "gclid", "msclkid", "twclid", "mc_cid", "mc_eid",
    "ref", "_ga", "_gl",
})

_GOOGLE_NEWS_RE = re.compile(r"https://news\.google\.com/rss/articles/(.+)")


def normalize_url(url: str) -> str:
    """Return a cleaned, canonical URL suitable for dedup."""
    if not url:
        return url

    # Google News redirect — unwrap real URL if possible
    # (full unwrap requires HTTP request; skip here, just normalize)

    try:
        parsed = urlparse(url.strip())
    except Exception:
        return url

    # Lowercase scheme and netloc
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Strip tracking query params
    qs = parse_qs(parsed.query, keep_blank_values=False)
    cleaned_qs = {k: v for k, v in qs.items() if k.lower() not in _TRACKING_PARAMS}
    query = urlencode(sorted(cleaned_qs.items()), doseq=True)

    # Remove fragment
    cleaned = urlunparse((scheme, netloc, parsed.path.rstrip("/") or "/", "", query, ""))
    return cleaned
