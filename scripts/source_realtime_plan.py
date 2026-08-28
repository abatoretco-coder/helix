#!/usr/bin/env python3
"""Build a freshness and quality plan from config/sources.yaml.

The goal is to make source expansion deliberate: more feeds, but with a clear
cadence budget and recommendations for what to accelerate, slow down, or review.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


DEFAULT_PATH = Path("config/sources.yaml")

REALTIME_CATEGORIES = {
    "general",
    "geopolitics",
    "finance",
    "cybersecurity",
    "ai",
    "tech",
    "regulation",
    "supply_chain",
    "climate",
}

TARGET_REFRESH_BY_PRIORITY = {
    1: 30,
    2: 45,
    3: 120,
    4: 360,
}


def _load_sources(path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources = data.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("Top-level 'sources' must be a list")
    return [source for source in sources if isinstance(source, dict)]


def _enabled(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [source for source in sources if source.get("enabled", True)]


def _source_name(source: dict[str, Any]) -> str:
    return str(source.get("name") or "<unnamed>")


def _priority(source: dict[str, Any]) -> int:
    try:
        return int(source.get("priority", 3))
    except (TypeError, ValueError):
        return 3


def _refresh(source: dict[str, Any]) -> int:
    try:
        return int(source.get("refresh_minutes", 60))
    except (TypeError, ValueError):
        return 60


def _collection_load_per_day(sources: list[dict[str, Any]]) -> float:
    total = 0.0
    for source in sources:
        refresh = max(_refresh(source), 1)
        total += 1440 / refresh
    return total


def _recommendations(sources: list[dict[str, Any]]) -> list[str]:
    recommendations: list[str] = []
    by_language = Counter(str(source.get("language") or "<missing>").lower() for source in sources)
    by_category = Counter(str(source.get("category") or "general").lower() for source in sources)
    by_type = Counter(str(source.get("type") or "<missing>").lower() for source in sources)

    french_share = by_language["fr"] / max(len(sources), 1)
    if french_share < 0.40:
        recommendations.append(
            f"Increase French coverage: FR sources are {french_share:.0%} of enabled sources; target at least 40%."
        )

    if by_type["google_news_rss"] < 80:
        recommendations.append(
            "Add targeted Google News RSS radars for fast-moving topics; they are useful for near-real-time discovery."
        )

    for category in sorted(REALTIME_CATEGORIES):
        count = by_category[category]
        if count < 5:
            recommendations.append(f"Add more '{category}' sources; current enabled coverage is only {count}.")

    too_slow_priority_1 = [
        source for source in sources
        if _priority(source) == 1 and _refresh(source) > TARGET_REFRESH_BY_PRIORITY[1]
    ]
    if too_slow_priority_1:
        names = ", ".join(_source_name(source) for source in too_slow_priority_1[:8])
        recommendations.append(
            f"Accelerate priority-1 sources to {TARGET_REFRESH_BY_PRIORITY[1]} minutes where safe: {names}."
        )

    noisy_fast = [
        source for source in sources
        if _priority(source) >= 3 and _refresh(source) < TARGET_REFRESH_BY_PRIORITY[3]
    ]
    if noisy_fast:
        names = ", ".join(_source_name(source) for source in noisy_fast[:8])
        recommendations.append(
            f"Slow low-priority sources to protect extraction capacity: {names}."
        )

    metadata_optional_types = {"github_trending", "youtube_channel"}
    missing_country = [
        source for source in sources
        if str(source.get("type") or "").lower() not in metadata_optional_types and not source.get("country")
    ]
    missing_language = [
        source for source in sources
        if str(source.get("type") or "").lower() not in metadata_optional_types and not source.get("language")
    ]
    if missing_country or missing_language:
        recommendations.append(
            f"Review metadata: {len(missing_country)} sources missing country, {len(missing_language)} missing language."
        )

    if not recommendations:
        recommendations.append("Registry shape is coherent; next gains should come from runtime health data.")
    return recommendations


def _print_counter(title: str, counter: Counter[str], limit: int = 20) -> None:
    print(f"\n## {title}")
    for key, count in counter.most_common(limit):
        print(f"- {key}: {count}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze source freshness coverage and print a roadmap.")
    parser.add_argument("--path", default=str(DEFAULT_PATH), help="Path to config/sources.yaml")
    parser.add_argument("--top", type=int, default=20, help="Number of source rows to show in top lists")
    args = parser.parse_args()

    path = Path(args.path)
    sources = _load_sources(path)
    enabled = _enabled(sources)

    by_type = Counter(str(source.get("type") or "<missing>").lower() for source in enabled)
    by_language = Counter(str(source.get("language") or "<missing>").lower() for source in enabled)
    by_category = Counter(str(source.get("category") or "general").lower() for source in enabled)
    by_priority = Counter(str(_priority(source)) for source in enabled)
    by_refresh = Counter(str(_refresh(source)) for source in enabled)

    print("# Helix source real-time plan")
    print(f"\nSources: {len(sources)} total, {len(enabled)} enabled")
    print(f"Estimated collection attempts/day: {_collection_load_per_day(enabled):.0f}")

    _print_counter("Types", by_type)
    _print_counter("Languages", by_language)
    _print_counter("Categories", by_category)
    _print_counter("Priorities", by_priority)
    _print_counter("Refresh minutes", by_refresh)

    print("\n## Fastest enabled sources")
    fastest = sorted(enabled, key=lambda source: (_refresh(source), _priority(source), _source_name(source)))
    for source in fastest[: args.top]:
        print(
            f"- {_source_name(source)} | p{_priority(source)} | "
            f"{_refresh(source)}m | {source.get('type')} | {source.get('category')} | {source.get('language')}"
        )

    print("\n## Recommendations")
    for index, recommendation in enumerate(_recommendations(enabled), start=1):
        print(f"{index}. {recommendation}")

    print("\n## Roadmap")
    print("1. Keep priority-1 sources at 30 minutes by default; reserve 15 minutes for breaking and critical cyber radars.")
    print("2. Use Google News RSS as fast radars, then replace noisy queries with direct RSS feeds when identified.")
    print("3. Review `/v1/sources/health` weekly: disable broken feeds, slow noisy feeds, boost high-value feeds.")
    print("4. Review citation coverage after runtime data confirms which sources consistently convert to articles.")
    print("5. Review persisted OpenAI usage and set request caps before changing any background AI setting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
