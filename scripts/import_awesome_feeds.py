#!/usr/bin/env python3
"""
Import RSS sources from https://github.com/plenaryapp/awesome-rss-feeds

This script:
  1. Clones (or pulls) the awesome-rss-feeds repo
  2. Parses all OPML files in the repo
  3. Generates new entries in config/sources.yaml (deduped by URL)

Usage:
  python scripts/import_awesome_feeds.py [--output config/sources.yaml] [--categories tech,ai,world]

The repo contains OPML files organised by country/language/category.
We filter by categories of interest and append to sources.yaml.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

import yaml

REPO_URL   = "https://github.com/plenaryapp/awesome-rss-feeds"
CLONE_DIR  = Path(__file__).parent.parent / "data" / "awesome-rss-feeds"

# Categories in awesome-rss-feeds we want to import
WANTED_CATEGORIES = {
    "technology", "tech", "ai", "science", "programming", "security",
    "cybersecurity", "startups", "business", "news", "world", "france",
    "english", "hacker-news", "reddit",
}

# Map awesome-rss-feeds folder names to our categories
CATEGORY_MAP: dict[str, str] = {
    "technology": "tech",
    "tech": "tech",
    "programming": "tech",
    "ai": "ai",
    "science": "tech",
    "security": "tech",
    "cybersecurity": "tech",
    "startups": "startups",
    "business": "finance",
    "news": "general",
    "world": "geopolitics",
    "france": "geopolitics",
    "english": "general",
}


def _clone_or_pull() -> None:
    if CLONE_DIR.exists():
        print(f"[awesome-rss-feeds] Pulling latest from {CLONE_DIR}")
        subprocess.run(["git", "-C", str(CLONE_DIR), "pull", "--quiet"], check=True)
    else:
        CLONE_DIR.parent.mkdir(parents=True, exist_ok=True)
        print(f"[awesome-rss-feeds] Cloning {REPO_URL} → {CLONE_DIR}")
        subprocess.run(["git", "clone", "--depth=1", REPO_URL, str(CLONE_DIR)], check=True)


def _parse_opml(opml_path: Path, category: str) -> list[dict]:
    """Parse a single OPML file and return list of source dicts."""
    sources = []
    try:
        tree = ElementTree.parse(opml_path)
    except ElementTree.ParseError as exc:
        print(f"  [skip] Parse error in {opml_path.name}: {exc}")
        return []

    for outline in tree.iter("outline"):
        url  = outline.get("xmlUrl") or outline.get("htmlUrl")
        name = outline.get("title") or outline.get("text") or ""
        if not url or not url.startswith("http"):
            continue
        sources.append({
            "name": name.strip()[:80],
            "type": "rss",
            "url": url.strip(),
            "category": category,
            "language": "en",
            "country": "global",
            "priority": 2,
            "refresh_minutes": 60,
            "extraction_strategy": "rss_then_article",
            "enabled": True,
        })
    return sources


def _load_existing_sources(output_path: Path) -> tuple[dict, set[str]]:
    """Load existing sources.yaml. Returns (full_yaml_dict, set_of_known_urls)."""
    if not output_path.exists():
        return {"sources": []}, set()
    with open(output_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {"sources": []}
    known_urls = {s.get("url", "") for s in data.get("sources", [])}
    return data, known_urls


def main():
    parser = argparse.ArgumentParser(description="Import feeds from awesome-rss-feeds")
    parser.add_argument("--output", default="config/sources.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be added without writing")
    parser.add_argument("--limit", type=int, default=200, help="Max feeds to add per run")
    parser.add_argument("--all-categories", action="store_true", help="Import from all OPML categories, not only the curated subset")
    args = parser.parse_args()

    output_path = Path(args.output)

    # 1. Clone / update the repo
    _clone_or_pull()

    # 2. Find OPML files
    opml_files = list(CLONE_DIR.rglob("*.opml"))
    if not opml_files:
        print("[error] No OPML files found in repo. Check clone path.")
        sys.exit(1)
    print(f"[awesome-rss-feeds] Found {len(opml_files)} OPML files")

    # 3. Load existing sources (to avoid duplicates)
    existing_data, known_urls = _load_existing_sources(output_path)

    # 4. Parse relevant OPML files
    new_sources: list[dict] = []
    for opml_path in sorted(opml_files):
        # Determine category from directory name
        folder = opml_path.parent.name.lower()
        category = CATEGORY_MAP.get(folder)
        if category is None:
            # Try grandparent
            category = CATEGORY_MAP.get(opml_path.parent.parent.name.lower())
        if (not args.all_categories) and category is None and folder not in WANTED_CATEGORIES:
            continue  # Skip unrelated categories

        if category is None:
            category = opml_path.parent.parent.name.lower().replace("_", "-") if args.all_categories else "general"
        category = category or "general"
        sources = _parse_opml(opml_path, category)

        for s in sources:
            if s["url"] in known_urls:
                continue
            known_urls.add(s["url"])
            new_sources.append(s)
            if len(new_sources) >= args.limit:
                break

        if len(new_sources) >= args.limit:
            break

    print(f"[awesome-rss-feeds] {len(new_sources)} new sources to add")

    if args.dry_run:
        for s in new_sources[:10]:
            print(f"  + [{s['category']}] {s['name']} — {s['url']}")
        if len(new_sources) > 10:
            print(f"  ... and {len(new_sources) - 10} more")
        return

    if not new_sources:
        print("[awesome-rss-feeds] Nothing new to add.")
        return

    # 5. Append to sources.yaml
    existing_data["sources"].extend(new_sources)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(existing_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"[awesome-rss-feeds] Written {len(new_sources)} new sources to {output_path}")


if __name__ == "__main__":
    main()
