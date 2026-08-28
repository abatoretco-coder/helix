"""Deterministic admission control for the Helix ingestion pipeline.

The policy deliberately runs before extraction and LLM work.  It is cheap,
auditable and configured from ``config/source_policy.yaml`` so a source can be
enabled in the catalogue without automatically consuming local-model capacity.
"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


POLICY_PATH = os.environ.get("SOURCE_POLICY_PATH", "/app/config/source_policy.yaml")


@dataclass(frozen=True)
class Decision:
    accepted: bool
    reason: str


def _normalise(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text).strip().lower()


@lru_cache(maxsize=2)
def _policy(path: str = POLICY_PATH) -> dict[str, Any]:
    policy_file = Path(path)
    if not policy_file.exists():
        return {"enabled": False}
    with policy_file.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {"enabled": False}


def reload_policy() -> None:
    _policy.cache_clear()


def _values(policy: dict[str, Any], key: str) -> set[str]:
    return {_normalise(value) for value in (policy.get(key) or []) if _normalise(value)}


def _contains_term(haystack: str, term: str) -> bool:
    """Match whole terms, preventing `ai` from matching words like `rainbow`."""
    return bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", haystack))


def _advertising_decision(source, title: str | None, snippet: str | None = None) -> Decision | None:
    """Reject commercial material without rejecting reporting *about* commerce.

    The source, headline and available body are checked.  Direct sponsorship
    disclosures are always rejected; generic marketing language must match a
    transactional pattern configured in ``source_policy.yaml``.
    """
    policy = _policy()
    guard = policy.get("advertising_filter") or {}
    if not guard.get("enabled", True):
        return None

    source_text = _normalise(
        f"{getattr(source, 'name', '') or ''} {getattr(source, 'url', '') or ''}"
    )
    if any(_contains_term(source_text, term) for term in _values(guard, "block_source_terms")):
        return Decision(False, "commercial_source")

    source_url = _normalise(getattr(source, "url", ""))
    if any(pattern in source_url for pattern in _values(guard, "block_url_patterns")):
        return Decision(False, "commercial_source_url")

    haystack = _normalise(f"{title or ''} {snippet or ''}")
    if any(_contains_term(haystack, term) for term in _values(guard, "disclosure_terms")):
        return Decision(False, "sponsored_or_affiliate_content")
    if any(_contains_term(haystack, term) for term in _values(guard, "promotional_terms")):
        return Decision(False, "promotional_content")

    for pattern in guard.get("promotional_patterns") or []:
        try:
            if re.search(str(pattern), haystack, flags=re.IGNORECASE):
                return Decision(False, "promotional_buying_guide")
        except re.error:
            # A malformed configuration must not stop collection.
            continue
    return None


def source_decision(source) -> Decision:
    policy = _policy()
    if not policy.get("enabled", True):
        return Decision(True, "policy_disabled")

    commercial = _advertising_decision(source, None)
    if commercial:
        return commercial

    category = _normalise(getattr(source, "category", ""))
    name = _normalise(getattr(source, "name", ""))
    source_type = _normalise(getattr(source, "source_type", ""))
    allowed_names = _values(policy, "allow_sources")
    blocked_names = _values(policy, "block_sources")
    blocked_source_types = _values(policy, "block_source_types")
    allowed_categories = _values(policy, "allow_categories")
    blocked_categories = _values(policy, "block_categories")

    if name in blocked_names:
        return Decision(False, "source_blocked")
    if source_type in blocked_source_types:
        return Decision(False, f"source_type_blocked:{source_type or 'unknown'}")
    if category in blocked_categories:
        return Decision(False, f"category_blocked:{category or 'unknown'}")
    if name in allowed_names:
        return Decision(True, "source_allowlisted")
    if allowed_categories and category not in allowed_categories:
        return Decision(False, f"category_not_allowlisted:{category or 'unknown'}")
    return Decision(True, "source_category_allowed")


def item_decision(source, title: str | None, snippet: str | None = None, published_at: datetime | None = None) -> Decision:
    decision = source_decision(source)
    if not decision.accepted:
        return decision

    policy = _policy()
    if not policy.get("enabled", True):
        return decision

    commercial = _advertising_decision(source, title, snippet)
    if commercial:
        return commercial

    max_age_days = int(policy.get("max_candidate_age_days", 7))
    if isinstance(published_at, datetime):
        published = published_at if published_at.tzinfo else published_at.replace(tzinfo=timezone.utc)
        if published < datetime.now(timezone.utc) - timedelta(days=max_age_days):
            return Decision(False, "candidate_too_old")

    category = _normalise(getattr(source, "category", ""))
    keyword_categories = _values(policy, "keyword_required_categories")
    if category not in keyword_categories:
        return Decision(True, decision.reason)

    haystack = _normalise(f"{title or ''} {snippet or ''}")
    required_terms = _values(policy, "relevance_terms")
    if any(_contains_term(haystack, term) for term in required_terms):
        return Decision(True, "keyword_match")
    return Decision(False, "missing_relevance_keyword")


def article_decision(article) -> Decision:
    source = getattr(article, "source", None)
    return item_decision(
        source,
        getattr(article, "title", None),
        f"{getattr(article, 'description', '') or ''} {getattr(article, 'text_content', '') or ''}",
        getattr(article, "published_at", None) or getattr(article, "discovered_at", None),
    )
