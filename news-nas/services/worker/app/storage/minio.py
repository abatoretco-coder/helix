"""MinIO raw storage — HTML and JSON dumps."""
import io
import os
from datetime import datetime
from pathlib import PurePosixPath

from minio import Minio
from minio.error import S3Error

_client: Minio = None
BUCKET = "news-raw"


def _get_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            os.environ["MINIO_ENDPOINT"],
            access_key=os.environ["MINIO_ACCESS_KEY"],
            secret_key=os.environ["MINIO_SECRET_KEY"],
            secure=False,
        )
        try:
            if not _client.bucket_exists(BUCKET):
                _client.make_bucket(BUCKET)
        except S3Error:
            pass
    return _client


def store_raw_html(article_id: int, source_slug: str, html: str) -> str:
    """Store raw HTML. Returns the MinIO object path."""
    now = datetime.utcnow()
    path = f"raw_html/{now.year}/{now.month:02d}/{now.day:02d}/{source_slug}/{article_id}.html"
    data = html.encode("utf-8")
    _get_client().put_object(BUCKET, path, io.BytesIO(data), len(data), content_type="text/html")
    return path


def store_raw_json(article_id: int, source_slug: str, payload: dict) -> str:
    """Store raw JSON payload. Returns the MinIO object path."""
    import json
    now = datetime.utcnow()
    path = f"raw_json/{now.year}/{now.month:02d}/{now.day:02d}/{source_slug}/{article_id}.json"
    data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
    _get_client().put_object(BUCKET, path, io.BytesIO(data), len(data), content_type="application/json")
    return path
