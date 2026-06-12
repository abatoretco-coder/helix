"""
Shared database utilities for workers.
Uses synchronous SQLAlchemy for simplicity in worker processes.
"""
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base, RawItem, Article, Source, ProcessingLog

# Workers use sync engine (workers are simple loops, no need for asyncio)
_engine = create_engine(
    # Workers use psycopg2 (sync). Strip +asyncpg suffix if present.
    os.environ["DATABASE_URL"].replace("+asyncpg", ""),
    pool_pre_ping=True,
    pool_size=5,
)
SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def upsert_raw_item(
    session: Session,
    source_id: int,
    url: str,
    normalized_url: str,
    title: Optional[str],
    snippet: Optional[str],
    published_at: Optional[datetime],
    raw_payload: dict,
) -> Optional[int]:
    """Insert raw_item if normalized_url not seen. Returns new id or None if duplicate."""
    existing = session.execute(
        select(RawItem.id).where(RawItem.normalized_url == normalized_url)
    ).scalar_one_or_none()

    if existing:
        return None

    item = RawItem(
        source_id=source_id,
        url=url,
        normalized_url=normalized_url,
        title=title,
        snippet=snippet,
        published_at=published_at,
        discovered_at=datetime.now(timezone.utc),
        raw_payload=raw_payload,
        status="new",
    )
    session.add(item)
    session.flush()
    return item.id


def mark_raw_item_status(session: Session, item_id: int, status: str, error: Optional[str] = None):
    session.execute(
        update(RawItem)
        .where(RawItem.id == item_id)
        .values(status=status, error_message=error, updated_at=datetime.now(timezone.utc))
    )


def mark_source_success(session: Session, source_id: int):
    now = datetime.now(timezone.utc)
    session.execute(
        update(Source)
        .where(Source.id == source_id)
        .values(last_checked_at=now, last_success_at=now, error_count=0)
    )


def mark_source_error(session: Session, source_id: int, error: str):
    session.execute(
        update(Source)
        .where(Source.id == source_id)
        .values(last_checked_at=datetime.now(timezone.utc), error_count=Source.error_count + 1)
    )


def log_processing(
    session: Session,
    item_type: str,
    item_id: Optional[int],
    step: str,
    status: str,
    message: Optional[str] = None,
    payload: Optional[dict] = None,
    duration_ms: Optional[int] = None,
):
    log = ProcessingLog(
        item_type=item_type,
        item_id=item_id,
        step=step,
        status=status,
        message=message,
        payload=payload,
        duration_ms=duration_ms,
    )
    session.add(log)
