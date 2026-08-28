"""Print a source viability report without changing the database.

Run inside the worker container:
``python -m app.tools.source_viability``
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from collections import defaultdict

from sqlalchemy import select

from app.db.models import Article, ArticleAI, Source
from app.policy.relevance import item_decision, source_decision
from app.storage.postgres import get_session


def main() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    with get_session() as session:
        sources = session.execute(select(Source).where(Source.enabled == True)).scalars().all()
        articles = session.execute(
            select(Article, ArticleAI, Source)
            .join(Source, Source.id == Article.source_id)
            .outerjoin(ArticleAI, ArticleAI.article_id == Article.id)
            .where(Article.created_at >= cutoff)
        ).all()

    metrics: dict[int, dict[str, int]] = defaultdict(lambda: {"articles": 0, "commercial": 0, "factful": 0})
    commercial_reasons = {
        "commercial_source", "commercial_source_url", "sponsored_or_affiliate_content",
        "promotional_content", "promotional_buying_guide",
    }
    for article, ai, source in articles:
        stats = metrics[int(source.id)]
        stats["articles"] += 1
        decision = item_decision(
            source, article.title, f"{article.description or ''} {article.text_content or ''}", article.published_at or article.discovered_at,
        )
        if decision.reason in commercial_reasons:
            stats["commercial"] += 1
        if ai and len((ai.summary_short or "").strip()) >= 90:
            stats["factful"] += 1

    print("# Helix source viability report")
    print(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    print("| Recommendation | Source | Category | Articles (7d) | Promo | Factual summaries | Reason |")
    print("|---|---|---|---:|---:|---:|---|")
    for source in sorted(sources, key=lambda value: (-metrics[int(value.id)]["articles"], value.name or "")):
        decision = source_decision(source)
        stats = metrics[int(source.id)]
        article_count = stats["articles"]
        commercial_ratio = stats["commercial"] / article_count if article_count else 0.0
        factual_ratio = stats["factful"] / article_count if article_count else 0.0
        if not decision.accepted:
            recommendation = "suspend"
        elif commercial_ratio >= 0.10:
            recommendation = "suspend"
        elif commercial_ratio > 0 or (article_count >= 5 and factual_ratio < 0.60):
            recommendation = "review"
        else:
            recommendation = "keep"
        source_name = (source.name or "").replace("|", "/")
        print(
            f"| {recommendation} | {source_name} | {source.category or ''} | {article_count} | "
            f"{stats['commercial']} ({commercial_ratio:.0%}) | {stats['factful']} ({factual_ratio:.0%}) | {decision.reason} |"
        )


if __name__ == "__main__":
    main()
