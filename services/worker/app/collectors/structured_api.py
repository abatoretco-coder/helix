"""Collectors for public structured-information APIs.

These APIs are deliberately converted to source-backed factual records before
they enter the normal Helix extraction/AI pipeline.  They are not scraped as
web pages: their JSON fields remain the evidence available to Ollama.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from app.utils.logging import get_logger

log = get_logger("collector.structured_api")
_HEADERS = {"Accept": "application/json", "User-Agent": "Helix/1.0"}


def _iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None


def _item(url: str, title: str, text: str, published_at: datetime | None, payload: dict[str, Any]) -> dict:
    evidence = " ".join(str(text or "").split())
    return {
        "url": url,
        "title": title,
        "snippet": evidence[:1200],
        "published_at": published_at,
        "raw_payload": {**payload, "structured_content": evidence},
    }


def collect_cisa_kev(source: dict, max_items: int = 25) -> list[dict]:
    """CISA's public catalogue of vulnerabilities known to be exploited."""
    response = requests.get(source["url"], headers=_HEADERS, timeout=30)
    response.raise_for_status()
    items: list[dict] = []
    vulnerabilities = response.json().get("vulnerabilities", [])
    for vuln in sorted(vulnerabilities, key=lambda value: str(value.get("dateAdded") or ""), reverse=True)[:max_items]:
        cve = str(vuln.get("cveID") or "")
        if not cve:
            continue
        date_added = _iso(vuln.get("dateAdded"))
        text = (
            f"CISA lists {cve} as known exploited. Vendor: {vuln.get('vendorProject') or 'unknown'}; "
            f"product: {vuln.get('product') or 'unknown'}. {vuln.get('vulnerabilityName') or ''}. "
            f"Required action: {vuln.get('requiredAction') or 'consult CISA guidance'}."
        )
        items.append(_item(
            f"https://www.cisa.gov/known-exploited-vulnerabilities-catalog?search_api_fulltext={cve}",
            f"[CISA KEV] {cve} — {vuln.get('vulnerabilityName') or 'known exploited vulnerability'}",
            text,
            date_added,
            {"cve": cve, "date_added": vuln.get("dateAdded"), "due_date": vuln.get("dueDate")},
        ))
    return items


def collect_github_advisories(source: dict, max_items: int = 30) -> list[dict]:
    response = requests.get(source["url"], headers=_HEADERS, params={"per_page": max_items, "type": "reviewed"}, timeout=30)
    response.raise_for_status()
    items: list[dict] = []
    for advisory in response.json():
        # The global feed is extremely broad.  In the real initial sample,
        # "high" mostly meant product-specific vulnerabilities with no
        # operational relevance to Helix; critical advisories are the useful
        # interrupt signal.  Other severities remain available from GitHub for
        # on-demand research rather than polluting the Flash Info stream.
        if str(advisory.get("severity") or "").lower() != "critical":
            continue
        url = advisory.get("html_url") or advisory.get("url")
        if not url:
            continue
        identifiers = ", ".join(item.get("value", "") for item in advisory.get("identifiers", []) if item.get("value"))
        text = (
            f"GitHub Security Advisory {advisory.get('ghsa_id') or ''}. Severity: {advisory.get('severity') or 'unknown'}. "
            f"{advisory.get('summary') or ''}. {advisory.get('description') or ''} Identifiers: {identifiers}."
        )
        items.append(_item(
            url,
            f"[GitHub Advisory] {advisory.get('ghsa_id') or ''} — {advisory.get('summary') or 'security advisory'}",
            text,
            _iso(advisory.get("published_at") or advisory.get("updated_at")),
            {"ghsa_id": advisory.get("ghsa_id"), "cve_id": advisory.get("cve_id"), "severity": advisory.get("severity")},
        ))
    return items


def collect_github_releases(source: dict, max_items: int = 20) -> list[dict]:
    repo = str(source.get("query") or "").strip()
    if not repo or "/" not in repo:
        raise ValueError("github_release source query must be owner/repository")
    response = requests.get(
        f"https://api.github.com/repos/{repo}/releases",
        headers=_HEADERS,
        params={"per_page": max_items},
        timeout=30,
    )
    response.raise_for_status()
    items: list[dict] = []
    for release in response.json():
        url = release.get("html_url")
        if not url:
            continue
        assets = ", ".join(asset.get("name", "") for asset in release.get("assets", [])[:8])
        text = (
            f"Release {release.get('tag_name') or ''} of {repo}. {release.get('name') or ''}. "
            f"{release.get('body') or 'No release notes provided.'} Assets: {assets}."
        )
        items.append(_item(url, f"[GitHub Release] {repo} {release.get('tag_name') or ''}", text,
                           _iso(release.get("published_at") or release.get("created_at")),
                           {"repository": repo, "tag": release.get("tag_name"), "prerelease": release.get("prerelease", False)}))
    return items


def _openalex_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    if not inverted_index:
        return ""
    words: dict[int, str] = {}
    for word, positions in inverted_index.items():
        for position in positions:
            words[int(position)] = word
    return " ".join(words[position] for position in sorted(words))


def collect_openalex(source: dict, max_items: int = 12) -> list[dict]:
    query = str(source.get("query") or "").strip()
    params: dict[str, Any] = {"per-page": max_items}
    if query:
        since = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
        # Keep discovery fresh: we want recent research signals, not a static
        # ranking of highly cited historical papers.
        params.update({"search": query, "filter": f"from_publication_date:{since}"})
    response = requests.get(source["url"], headers=_HEADERS, params=params, timeout=30)
    response.raise_for_status()
    items: list[dict] = []
    for work in response.json().get("results", []):
        url = work.get("doi") or work.get("id")
        title = work.get("title") or ""
        if not url or not title:
            continue
        abstract = _openalex_abstract(work.get("abstract_inverted_index"))
        concepts = ", ".join(concept.get("display_name", "") for concept in work.get("concepts", [])[:6])
        text = f"Research publication: {title}. {abstract}. Concepts: {concepts}."
        items.append(_item(url, f"[OpenAlex] {title}", text, _iso(work.get("publication_date")),
                           {"openalex_id": work.get("id"), "doi": work.get("doi"), "cited_by_count": work.get("cited_by_count")}))
    return items


def collect_eurostat(source: dict) -> list[dict]:
    """Turn one filtered JSON-stat dataset response into a dated data event."""
    response = requests.get(source["url"], headers=_HEADERS, timeout=30)
    response.raise_for_status()
    data = response.json()
    dimensions = data.get("dimension") or {}
    time_dimension = dimensions.get("time") or dimensions.get("TIME_PERIOD") or {}
    labels = ((time_dimension.get("category") or {}).get("label") or {})
    periods = sorted(labels)
    if not periods:
        return []
    period = periods[-1]
    values = data.get("value") or {}
    value = next(reversed(values.values()), None) if isinstance(values, dict) and values else None
    dataset_label = str(data.get("label") or source.get("name") or "Eurostat dataset")
    text = f"Eurostat update for {dataset_label}. Latest reported period: {period}. Latest available value: {value}."
    return [_item(f"{source['url']}#period={period}&value={value}", f"[Eurostat] {dataset_label} — {period}", text,
                  datetime.now(timezone.utc),
                  {"dataset_label": dataset_label, "period": period, "value": value})]


def collect_datagouv_dataset(source: dict) -> list[dict]:
    """Expose a data.gouv.fr dataset revision as a traceable reference event.

    A dataset publication is not a news article.  We retain its official
    description, revision timestamp and resource inventory so Helix can answer
    data questions with provenance, while the public Flash Info excludes this
    source type.  The stable revision timestamp in the URL deduplicates every
    polling cycle; only a real publisher update creates a new event.
    """
    response = requests.get(source["url"], headers=_HEADERS, timeout=30)
    response.raise_for_status()
    dataset = response.json()
    title = str(dataset.get("title") or source.get("name") or "data.gouv.fr dataset").strip()
    modified = _iso(str(dataset.get("last_modified") or dataset.get("last_update") or ""))
    if not modified:
        return []
    resources = dataset.get("resources") or []
    resource_names = "; ".join(str(resource.get("title") or resource.get("name") or "resource") for resource in resources[:12])
    description = " ".join(str(dataset.get("description") or "").split())
    text = (
        f"Official data.gouv.fr dataset: {title}. Last official update: {modified.date().isoformat()}. "
        f"{description} Available resources ({len(resources)}): {resource_names}."
    )
    dataset_url = dataset.get("page") or source["url"].replace("/api/1/datasets/", "/datasets/")
    revision_url = f"{dataset_url}#revision={modified.isoformat()}"
    return [_item(
        revision_url,
        f"[data.gouv.fr] {title} — mise à jour {modified.date().isoformat()}",
        text,
        modified,
        {
            "dataset_id": dataset.get("id"),
            "dataset_slug": dataset.get("slug"),
            "last_modified": modified.isoformat(),
            "resource_count": len(resources),
            "resources": [{"title": resource.get("title"), "url": resource.get("url")} for resource in resources[:12]],
        },
    )]
