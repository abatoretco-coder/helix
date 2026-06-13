#!/usr/bin/env python3
"""Export briefings from PostgreSQL into an Obsidian-friendly vault structure."""

from __future__ import annotations

import csv
import os
import pathlib
import subprocess
import sys
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
        "copy (select id, period, period_date, category, content, generated_at from briefings order by period_date desc, id desc) to stdout with csv header",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "psql export failed")
    return list(csv.DictReader(proc.stdout.splitlines()))


def _normalize_date(value: str) -> str:
    if not value:
        return datetime.utcnow().date().isoformat()
    return value.split(" ")[0]


def _build_markdown(row: dict[str, str]) -> str:
    briefing_id = row.get("id", "")
    period = row.get("period", "daily")
    period_date = _normalize_date(row.get("period_date", ""))
    category = row.get("category", "all")
    generated_at = row.get("generated_at", "")
    content = row.get("content", "")
    tags = ["helix", "briefing", f"period-{period}", f"category-{category}"]
    frontmatter = [
        "---",
        f"id: {briefing_id}",
        f"period: {period}",
        f"date: {period_date}",
        f"category: {category}",
        f"generated_at: {generated_at}",
        f"tags: [{', '.join(tags)}]",
        "---",
        "",
    ]
    return "\n".join(frontmatter) + content.strip() + "\n"


def main() -> int:
    vault_dir = _env("OBSIDIAN_VAULT_PATH")
    subdir = _env("OBSIDIAN_BRIEFINGS_DIR", "Helix/Briefings")

    if not vault_dir:
        print("[obsidian_export] OBSIDIAN_VAULT_PATH is empty. Skipping export.")
        return 0

    out_dir = pathlib.Path(vault_dir) / subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = _query_rows()
    exported = 0
    for row in rows:
        period = row.get("period", "daily")
        period_date = _normalize_date(row.get("period_date", ""))
        category = row.get("category", "all")
        briefing_id = row.get("id", str(exported + 1))
        filename = f"{period_date}_{period}_{category}_{briefing_id}.md".replace(":", "-")
        (out_dir / filename).write_text(_build_markdown(row), encoding="utf-8")
        exported += 1

    print(f"[obsidian_export] Exported {exported} briefings to {out_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[obsidian_export][error] {exc}", file=sys.stderr)
        raise SystemExit(1)
