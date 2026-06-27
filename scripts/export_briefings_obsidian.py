#!/usr/bin/env python3
"""Export briefings from PostgreSQL into an Obsidian-friendly vault structure."""

from __future__ import annotations

import csv
import os
import pathlib
import subprocess
import sys
import re
from datetime import datetime


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _query_rows() -> list[dict[str, str]]:
    db_user = _env("POSTGRES_USER", "news")
    db_name = _env("POSTGRES_DB", "newsdb")
    cmd = [
        "docker",
        "compose",
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        db_user,
        "-d",
        db_name,
        "-c",
        "copy (select id, period, period_date, category, content, generated_at, article_ids, cluster_ids from briefings order by period_date desc, id desc) to stdout with csv header",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "psql export failed")
    return list(csv.DictReader(proc.stdout.splitlines()))


def _normalize_date(value: str) -> str:
    if not value:
        return datetime.utcnow().date().isoformat()
    return value.split(" ")[0]


def _parse_pg_array(value: str) -> list[str]:
    if not value:
        return []
    text = value.strip()
    if text.startswith("{") and text.endswith("}"):
        text = text[1:-1]
    if not text:
        return []
    return [item.strip().strip('"') for item in text.split(",") if item.strip()]


def _build_markdown(row: dict[str, str]) -> str:
    period_date = _normalize_date(row.get("period_date", ""))
    category = row.get("category", "all") or "all"
    generated_at = row.get("generated_at", "") or ""
    content = (row.get("content", "") or "").strip()
    article_ids = _parse_pg_array(row.get("article_ids", "") or "")
    cluster_ids = _parse_pg_array(row.get("cluster_ids", "") or "")

    frontmatter = [
        "---",
        "type: daily_briefing",
        f"date: {period_date}",
        f"category: {category}",
        f"generated_at: {generated_at}",
        f"article_count: {len(article_ids)}",
        f"cluster_count: {len(cluster_ids)}",
        "source: helix",
        "---",
        "",
    ]

    body = [content or "No briefing content available."]
    if article_ids:
        body.extend(["", "## Source articles"])
        body.extend([f"- Article ID {article_id}" for article_id in article_ids])

    return "\n".join(frontmatter + body).strip() + "\n"


def _safe_file_slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", value)


def _build_index(items: list[dict[str, str]]) -> str:
    lines = ["# Helix Obsidian Briefings Index", ""]
    grouped: dict[str, list[dict[str, str]]] = {}
    for item in items:
        month = item["date"][:7]
        grouped.setdefault(month, []).append(item)

    for month in sorted(grouped.keys(), reverse=True):
        lines.append(f"## {month}")
        for row in grouped[month]:
            lines.append(f"- [[{row['note_path']}|{row['date']} {row['period']} {row['category']}]]")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    export_enabled = _env("OBSIDIAN_EXPORT_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
    if not export_enabled:
        print("[obsidian_export] OBSIDIAN_EXPORT_ENABLED=false. Skipping export.")
        return 0

    base_dir = pathlib.Path(_env("OBSIDIAN_EXPORT_PATH", "exports/obsidian"))
    out_root = base_dir / "briefings"
    out_root.mkdir(parents=True, exist_ok=True)

    rows = _query_rows()
    exported = 0
    index_rows: list[dict[str, str]] = []
    for row in rows:
        period = row.get("period", "daily")
        period_date = _normalize_date(row.get("period_date", ""))
        category = row.get("category", "all")
        year = period_date[:4]
        month = period_date[5:7]
        dir_path = out_root / year / month
        dir_path.mkdir(parents=True, exist_ok=True)

        filename = f"{period_date}_{_safe_file_slug(period)}_{_safe_file_slug(category)}.md"
        note_path = f"briefings/{year}/{month}/{filename}"
        (dir_path / filename).write_text(_build_markdown(row), encoding="utf-8")
        index_rows.append(
            {
                "date": period_date,
                "period": str(period or "daily"),
                "category": str(category or "all"),
                "note_path": note_path,
            }
        )
        exported += 1

    (out_root / "index.md").write_text(_build_index(index_rows), encoding="utf-8")

    print(f"[obsidian_export] Exported {exported} briefings to {out_root}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[obsidian_export][error] {exc}", file=sys.stderr)
        raise SystemExit(1)
