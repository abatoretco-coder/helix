#!/usr/bin/env python3
"""Append a curated Helix source pack to config/sources.yaml.

The pack is intentionally French-first, with complementary international feeds
and targeted Google News queries. It is safe to run repeatedly: source identity
is computed the same way as scripts/validate_sources.py.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


DEFAULT_PATH = Path("config/sources.yaml")


def rss(
    name: str,
    url: str,
    category: str,
    language: str,
    country: str,
    priority: int = 2,
    refresh_minutes: int = 45,
) -> dict[str, Any]:
    return {
        "name": name,
        "type": "rss",
        "url": url,
        "category": category,
        "language": language,
        "country": country,
        "priority": priority,
        "refresh_minutes": refresh_minutes,
        "extraction_strategy": "rss_then_article",
        "enabled": True,
    }


def google_news(
    name: str,
    query: str,
    category: str,
    language: str = "fr",
    country: str = "FR",
    priority: int = 2,
    refresh_minutes: int = 45,
) -> dict[str, Any]:
    return {
        "name": name,
        "type": "google_news_rss",
        "query": query,
        "category": category,
        "language": language,
        "country": country,
        "priority": priority,
        "refresh_minutes": refresh_minutes,
        "extraction_strategy": "rss_then_article",
        "enabled": True,
    }


def reddit(
    name: str,
    subreddit: str,
    category: str,
    language: str = "en",
    country: str = "global",
    priority: int = 3,
    refresh_minutes: int = 90,
) -> dict[str, Any]:
    return {
        "name": name,
        "type": "reddit",
        "subreddit": subreddit,
        "category": category,
        "language": language,
        "country": country,
        "priority": priority,
        "refresh_minutes": refresh_minutes,
        "extraction_strategy": "reddit",
        "enabled": True,
    }


CURATED_SOURCES: list[dict[str, Any]] = [
    # French direct feeds: general, economy, tech, cyber, science, policy.
    rss("Le Monde - Une", "https://www.lemonde.fr/rss/une.xml", "general", "fr", "FR", 1, 30),
    rss("Franceinfo - Titres", "https://www.francetvinfo.fr/titres.rss", "general", "fr", "FR", 1, 30),
    rss("Le Figaro - Actualites", "https://www.lefigaro.fr/rss/figaro_actualites.xml", "general", "fr", "FR", 2, 45),
    rss("Liberation - Tous les articles", "https://www.liberation.fr/arc/outboundfeeds/rss-all/?outputType=xml", "general", "fr", "FR", 2, 45),
    rss("20 Minutes - Une", "https://www.20minutes.fr/feeds/rss-une.xml", "general", "fr", "FR", 2, 45),
    rss("RFI - France", "https://www.rfi.fr/fr/france/rss", "general", "fr", "FR", 2, 45),
    rss("RFI - Monde", "https://www.rfi.fr/fr/monde/rss", "geopolitics", "fr", "FR", 2, 45),
    rss("France 24 - France", "https://www.france24.com/fr/france/rss", "general", "fr", "FR", 2, 45),
    rss("France 24 - Monde", "https://www.france24.com/fr/rss", "geopolitics", "fr", "FR", 2, 45),
    rss("La Tribune", "https://www.latribune.fr/feed.xml", "finance", "fr", "FR", 2, 45),
    rss("BFM Business - Economie", "https://www.bfmtv.com/rss/economie/", "finance", "fr", "FR", 2, 45),
    rss("Numerama", "https://www.numerama.com/feed/", "tech", "fr", "FR", 1, 30),
    rss("Siecle Digital", "https://siecledigital.fr/feed/", "tech", "fr", "FR", 1, 30),
    rss("ActuIA", "https://www.actuia.com/feed/", "ai", "fr", "FR", 1, 30),
    rss("CERT-FR", "https://www.cert.ssi.gouv.fr/feed/", "cybersecurity", "fr", "FR", 1, 30),
    rss("CNIL", "https://www.cnil.fr/fr/rss.xml", "regulation", "fr", "FR", 1, 60),
    rss("Futura Sciences", "https://www.futura-sciences.com/rss/actualites.xml", "science", "fr", "FR", 2, 60),
    rss("Vie Publique", "https://www.vie-publique.fr/rss.xml", "regulation", "fr", "FR", 2, 90),
    rss("Le Grand Continent", "https://legrandcontinent.eu/fr/feed/", "geopolitics", "fr", "FR", 2, 90),
    rss("The Conversation France", "https://theconversation.com/fr/articles.atom", "science", "fr", "FR", 2, 90),
    rss("Maddyness", "https://www.maddyness.com/feed/", "startups", "fr", "FR", 2, 45),
    rss("FrenchWeb", "https://www.frenchweb.fr/feed", "startups", "fr", "FR", 2, 45),
    rss("Next INpact", "https://next.ink/feed/", "tech", "fr", "FR", 1, 45),
    rss("ZDNet France", "https://www.zdnet.fr/feeds/rss/actualites/", "tech", "fr", "FR", 2, 45),
    rss("Clubic", "https://www.clubic.com/feed/news.rss", "tech", "fr", "FR", 2, 45),
    rss("Developpez.com", "https://www.developpez.com/index/rss", "tech", "fr", "FR", 2, 60),
    rss("Journal du Geek", "https://www.journaldugeek.com/feed/", "tech", "fr", "FR", 2, 45),
    rss("Presse Citron", "https://www.presse-citron.net/feed/", "tech", "fr", "FR", 2, 45),
    rss("Les Numeriques", "https://www.lesnumeriques.com/rss.xml", "tech", "fr", "FR", 2, 45),
    # International direct feeds with high signal for AI, cyber, science, infra.
    rss("The Hacker News", "https://feeds.feedburner.com/TheHackersNews", "cybersecurity", "en", "global", 1, 30),
    rss("BleepingComputer", "https://www.bleepingcomputer.com/feed/", "cybersecurity", "en", "global", 1, 30),
    rss("EFF Deeplinks", "https://www.eff.org/rss/updates.xml", "regulation", "en", "US", 2, 90),
    rss("MIT Technology Review", "https://www.technologyreview.com/feed/", "tech", "en", "US", 1, 45),
    rss("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index", "tech", "en", "US", 2, 45),
    rss("Nature", "https://www.nature.com/nature.rss", "science", "en", "global", 2, 120),
    rss("ScienceDaily", "https://www.sciencedaily.com/rss/top.xml", "science", "en", "US", 2, 90),
    rss("Google AI Blog", "https://blog.google/technology/ai/rss/", "ai", "en", "US", 1, 60),
    rss("DeepMind Blog", "https://deepmind.google/blog/rss.xml", "ai", "en", "GB", 1, 60),
    rss("Hugging Face Blog", "https://huggingface.co/blog/feed.xml", "ai", "en", "global", 1, 60),
    rss("Kubernetes Blog", "https://kubernetes.io/feed.xml", "tech", "en", "global", 2, 120),
    # French-first topic radars via Google News.
    google_news("Google News - IA France", "intelligence artificielle France", "ai", priority=1, refresh_minutes=30),
    google_news("Google News - Mistral AI France", "Mistral AI France", "ai", priority=1, refresh_minutes=30),
    google_news("Google News - OpenAI France", "OpenAI France", "ai", priority=2, refresh_minutes=45),
    google_news("Google News - Open Source IA France", "open source IA France", "ai", priority=2),
    google_news("Google News - Modeles IA Europe", "modele IA Europe open source", "ai", priority=2),
    google_news("Google News - Agents IA France", "agents IA France entreprise", "ai", priority=2),
    google_news("Google News - Regulation IA Europe", "reglementation IA Europe AI Act", "regulation", priority=1),
    google_news("Google News - Donnees personnelles CNIL", "donnees personnelles CNIL IA", "regulation", priority=1),
    google_news("Google News - Souverainete numerique", "souverainete numerique France Europe", "regulation", priority=2),
    google_news("Google News - Cloud souverain France", "cloud souverain France", "tech", priority=2),
    google_news("Google News - Cybersecurite France ANSSI", "cybersecurite France ANSSI", "cybersecurity", priority=1, refresh_minutes=30),
    google_news("Google News - Cyberattaque France", "cyberattaque France entreprise", "cybersecurity", priority=1, refresh_minutes=30),
    google_news("Google News - Vulnerabilite critique", "vulnerabilite critique exploitee", "cybersecurity", priority=1, refresh_minutes=30),
    google_news("Google News - French Tech Levees", "French Tech levee de fonds startup", "startups", priority=2),
    google_news("Google News - Deeptech France", "startup deeptech France", "startups", priority=2),
    google_news("Google News - Semi conducteurs Europe", "semi-conducteurs Europe France", "tech", priority=2),
    google_news("Google News - Quantique France", "quantique France calcul ordinateur", "science", priority=2),
    google_news("Google News - Robotique Logistique France", "robotique logistique France entrepot", "supply_chain", priority=2),
    google_news("Google News - Supply Chain France", "supply chain France logistique", "supply_chain", priority=2),
    google_news("Google News - Fret Ferroviaire France", "transport ferroviaire fret France", "supply_chain", priority=3),
    google_news("Google News - Transition Energetique France", "transition energetique France", "climate", priority=2),
    google_news("Google News - Nucleaire SMR France", "nucleaire France EPR SMR", "climate", priority=2),
    google_news("Google News - Hydrogen France", "hydrogene France industrie", "climate", priority=2),
    google_news("Google News - Batteries Gigafactory France", "batteries gigafactory France Europe", "climate", priority=2),
    google_news("Google News - Pharma France", "pharmaceutique France medicament", "pharma", priority=2),
    google_news("Google News - Biotech Sante France", "biotech France sante", "pharma", priority=2),
    google_news("Google News - Hopital Numerique France", "hopital numerique France sante", "pharma", priority=2),
    google_news("Google News - Agritech France", "agriculture technologie France agritech", "science", priority=3),
    google_news("Google News - Defense Innovation France", "defense France innovation technologie", "geopolitics", priority=2),
    google_news("Google News - Spatial France Europe", "spatial France Europe Ariane", "science", priority=2),
    google_news("Google News - Geopolitique Europe Afrique", "geopolitique Europe Afrique France", "geopolitics", priority=2),
    google_news("Google News - Ukraine Russie Europe", "Ukraine Russie Europe France", "geopolitics", priority=2),
    google_news("Google News - Chine Europe Commerce", "Chine Europe commerce industrie", "geopolitics", priority=2),
    google_news("Google News - Inflation France", "inflation France economie", "finance", priority=2),
    google_news("Google News - Immobilier Taux France", "immobilier France taux credit", "finance", priority=3),
    google_news("Google News - Crypto MiCA Europe", "regulation crypto Europe MiCA", "finance", priority=2),
    google_news("Google News - Education Numerique France", "education numerique France IA", "regulation", priority=3),
    google_news("Google News - Secteur Public IA France", "service public IA France administration", "regulation", priority=3),
    google_news("Google News - Medias IA France", "medias IA France droit auteur", "regulation", priority=3),
    google_news("Google News - Emploi IA France", "emploi IA France automatisation", "finance", priority=3),
    # International topic radars.
    google_news("Google News - AI Safety Regulation", "AI safety regulation", "ai", "en", "US", 2),
    google_news("Google News - AI Model Release", "open source AI model release", "ai", "en", "US", 2),
    google_news("Google News - Semiconductor Supply Chain", "semiconductors supply chain", "supply_chain", "en", "US", 2),
    google_news("Google News - Exploited Vulnerability", "cybersecurity vulnerability exploited", "cybersecurity", "en", "US", 1, 30),
    google_news("Google News - Pharma Supply Chain", "pharma supply chain", "pharma", "en", "US", 2),
    google_news("Google News - Energy Storage", "climate tech energy storage", "climate", "en", "US", 2),
    google_news("Google News - Defense Tech Europe", "defense technology Europe", "geopolitics", "en", "US", 2),
    google_news("Google News - Space Industry Launch", "space industry launch", "science", "en", "US", 2),
    google_news("Google News - Quantum Computing", "quantum computing breakthrough", "science", "en", "US", 2),
    google_news("Google News - Warehouse Robotics", "robotics warehouse automation", "supply_chain", "en", "US", 2),
    reddit("Reddit - francepolitique", "francepolitique", "geopolitics", "fr", "FR", 3, 120),
    reddit("Reddit - vosfinances", "vosfinances", "finance", "fr", "FR", 3, 120),
]


def _load_sources(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources = data.get("sources", [])
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


def _missing_sources(existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    known = {_source_identity(source) for source in existing}
    missing: list[dict[str, Any]] = []
    for source in CURATED_SOURCES:
        identity = _source_identity(source)
        if identity in known:
            continue
        known.add(identity)
        missing.append(source)
    return missing


def _append_sources(path: Path, sources: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = yaml.safe_dump(
        {"sources": sources},
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )
    entries = rendered.split("\n", 1)[1].rstrip()
    prefix = "\n" if path.exists() and path.read_text(encoding="utf-8").strip() else "sources:\n"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(prefix)
        handle.write(entries)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Append curated Helix sources")
    parser.add_argument("--path", default=str(DEFAULT_PATH), help="Source registry path")
    parser.add_argument("--dry-run", action="store_true", help="Show additions without writing")
    args = parser.parse_args()

    path = Path(args.path)
    existing = _load_sources(path)
    missing = _missing_sources(existing)

    print(f"[enrich-sources] existing={len(existing)} curated={len(CURATED_SOURCES)} add={len(missing)}")
    if missing:
        by_language = Counter(source.get("language", "") for source in missing)
        by_type = Counter(source.get("type", "") for source in missing)
        by_category = Counter(source.get("category", "") for source in missing)
        print(f"[enrich-sources] additions by language: {dict(sorted(by_language.items()))}")
        print(f"[enrich-sources] additions by type: {dict(sorted(by_type.items()))}")
        print(f"[enrich-sources] top categories: {by_category.most_common(10)}")

    if args.dry_run:
        for source in missing[:25]:
            detail = source.get("url") or source.get("query") or source.get("subreddit")
            print(f"  + [{source['language']}/{source['category']}] {source['name']} :: {detail}")
        if len(missing) > 25:
            print(f"  ... and {len(missing) - 25} more")
        return 0

    if not missing:
        print("[enrich-sources] Nothing new to add.")
        return 0

    _append_sources(path, missing)
    print(f"[enrich-sources] appended {len(missing)} sources to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
