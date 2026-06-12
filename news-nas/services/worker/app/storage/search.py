"""Meilisearch indexing helpers."""
import os
from meilisearch_python_sdk import Client

MEILI_URL = os.environ.get("MEILI_URL", "http://meilisearch:7700")
MEILI_KEY  = os.environ.get("MEILI_MASTER_KEY", "")

_client: Client = None


def get_meili() -> Client:
    global _client
    if _client is None:
        _client = Client(MEILI_URL, MEILI_KEY)
        _ensure_indexes()
    return _client


def _ensure_indexes():
    c = Client(MEILI_URL, MEILI_KEY)
    try:
        idx = c.index("articles")
    except Exception:
        c.create_index("articles", primary_key="id")
        idx = c.index("articles")

    idx.update_filterable_attributes([
        "source", "category", "language", "country", "published_at",
        "final_score", "quality_score", "cluster_id",
    ])
    idx.update_sortable_attributes(["published_at", "final_score"])
    idx.update_searchable_attributes([
        "title", "summary_short", "summary_long", "text_content",
        "source", "category", "topics", "entities",
    ])


def index_article(doc: dict) -> None:
    """Upsert a single article document into Meilisearch."""
    get_meili().index("articles").add_documents([doc])


def delete_article(article_id: int) -> None:
    get_meili().index("articles").delete_document(article_id)
