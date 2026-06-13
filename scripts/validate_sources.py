#!/usr/bin/env python3
"""Validate the Helix source registry.

This script checks the shape and consistency of config/sources.yaml so imports
and manual edits fail fast before they reach the pipeline.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml


ALLOWED_TYPES = {
    "rss",
    "google_news_rss",
    "reddit",
    "hackernews",
    "github_trending",
    "sitemap",
    "youtube",
    "youtube_channel",
}

ALLOWED_EXTRACTORS = {
    "article",
    "reddit",
    "github",
    "rss",
    "rss_then_article",
    "sitemap",
    "youtube",
}

REQUIRED_COMMON_KEYS = {
    "name",
    "type",
    "category",
    "priority",
    "refresh_minutes",
    "extraction_strategy",
    "enabled",
}


def _load_sources(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    sources = data.get("sources")
    if not isinstance(sources, list):
        raise ValueError("Top-level 'sources' must be a list")

    return sources


def _source_identity(source: dict[str, Any]) -> str:
    source_type = str(source.get("type", "")).strip().lower()

    if source_type in {"rss", "sitemap"}:
        return f"{source_type}:{str(source.get('url', '')).strip()}"
    if source_type == "google_news_rss":
        return (
            "google_news_rss:"
            f"{str(source.get('query', '')).strip().lower()}|"
            f"{str(source.get('language', '')).strip().lower()}|"
            f"{str(source.get('country', '')).strip().lower()}"
        )
    if source_type == "reddit":
        return f"reddit:{str(source.get('subreddit', '')).strip().lower()}"
    if source_type == "hackernews":
        return f"hackernews:{str(source.get('hn_type', '')).strip().lower()}"
    if source_type == "github_trending":
        return (
            "github_trending:"
            f"{str(source.get('topic', '')).strip().lower()}|"
            f"{str(source.get('language_filter', '')).strip().lower()}"
        )
    if source_type == "youtube_channel":
        return f"youtube_channel:{str(source.get('channel_id', '')).strip().lower()}"

    return f"{source_type}:{str(source.get('name', '')).strip().lower()}"


def validate_sources(path: Path) -> tuple[list[str], list[str]]:
    sources = _load_sources(path)
    errors: list[str] = []
    warnings: list[str] = []

    identities: dict[str, list[str]] = defaultdict(list)
    type_counts: Counter[str] = Counter()

    for index, raw_source in enumerate(sources, start=1):
        if not isinstance(raw_source, dict):
            errors.append(f"[{index}] source entry must be a mapping")
            continue

        name = str(raw_source.get("name", "")).strip()
        source_type = str(raw_source.get("type", "")).strip()
        if not name:
            errors.append(f"[{index}] missing name")
        if not source_type:
            errors.append(f"[{name or index}] missing type")

        missing = [key for key in REQUIRED_COMMON_KEYS if key not in raw_source]
        if missing:
            errors.append(f"[{name or index}] missing required keys: {', '.join(sorted(missing))}")

        if source_type and source_type not in ALLOWED_TYPES:
            warnings.append(f"[{name or index}] unknown source type '{source_type}'")

        extraction_strategy = str(raw_source.get("extraction_strategy", "")).strip()
        if extraction_strategy and extraction_strategy not in ALLOWED_EXTRACTORS:
            warnings.append(
                f"[{name or index}] unknown extraction strategy '{extraction_strategy}'"
            )

        priority = raw_source.get("priority")
        if not isinstance(priority, int) or priority < 1 or priority > 4:
            errors.append(f"[{name or index}] priority must be an integer between 1 and 4")

        refresh_minutes = raw_source.get("refresh_minutes")
        if not isinstance(refresh_minutes, int) or refresh_minutes <= 0:
            errors.append(f"[{name or index}] refresh_minutes must be a positive integer")

        if not isinstance(raw_source.get("enabled"), bool):
            errors.append(f"[{name or index}] enabled must be a boolean")

        language = str(raw_source.get("language", "")).strip()
        country = str(raw_source.get("country", "")).strip()
        if not language and source_type not in {"github_trending", "youtube_channel"}:
            warnings.append(f"[{name or index}] missing language")
        if not country and source_type not in {"github_trending", "youtube_channel"}:
            warnings.append(f"[{name or index}] missing country")

        if source_type == "rss" and not str(raw_source.get("url", "")).strip():
            errors.append(f"[{name or index}] rss sources require a url")
        elif source_type == "google_news_rss" and not str(raw_source.get("query", "")).strip():
            errors.append(f"[{name or index}] google_news_rss sources require a query")
        elif source_type == "reddit" and not str(raw_source.get("subreddit", "")).strip():
            errors.append(f"[{name or index}] reddit sources require a subreddit")
        elif source_type == "hackernews" and not str(raw_source.get("hn_type", "")).strip():
            errors.append(f"[{name or index}] hackernews sources require an hn_type")
        elif source_type == "github_trending" and not str(raw_source.get("topic", "")).strip():
            errors.append(f"[{name or index}] github_trending sources require a topic")
        elif source_type == "youtube_channel" and not str(raw_source.get("channel_id", "")).strip():
            errors.append(f"[{name or index}] youtube_channel sources require a channel_id")

        identity = _source_identity(raw_source)
        identities[identity].append(name or str(index))
        type_counts[source_type or "<missing>"] += 1

        if name and len(name) > 120:
            warnings.append(f"[{name}] name is longer than 120 characters")

    duplicate_identities = {key: values for key, values in identities.items() if len(values) > 1}
    for identity, refs in duplicate_identities.items():
        errors.append(f"duplicate source identity '{identity}' used by: {', '.join(refs)}")

    print(f"[validate-sources] scanned {len(sources)} sources")
    print("[validate-sources] type distribution:")
    for source_type, count in sorted(type_counts.items()):
        print(f"  - {source_type}: {count}")

    for warning in warnings:
        print(f"[warn] {warning}")

    for error in errors:
        print(f"[error] {error}")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate config/sources.yaml")
    parser.add_argument("--path", default="config/sources.yaml", help="Path to the sources YAML file")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on warnings as well as errors",
    )
    args = parser.parse_args()

    source_path = Path(args.path)
    if not source_path.exists():
        print(f"[validate-sources] file not found: {source_path}")
        return 1

    try:
        errors, warnings = validate_sources(source_path)
    except Exception as exc:  # pragma: no cover - defensive CLI entrypoint
        print(f"[validate-sources] failed: {exc}")
        return 1

    if errors:
        return 1

    if args.strict:
        print("[validate-sources] strict mode enabled: warnings must be reviewed manually")
        if warnings:
            return 1

    print("[validate-sources] ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())