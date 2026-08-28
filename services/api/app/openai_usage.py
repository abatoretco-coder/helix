from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OpenAIUsageEvent


def _limit(name: str) -> int:
    try:
        return max(0, int(os.environ.get(name, "0")))
    except ValueError:
        return 0


def _endpoint_limit_name(endpoint: str) -> str:
    return f"OPENAI_{endpoint.upper().replace('-', '_')}_DAILY_REQUEST_LIMIT"


async def _count_since(db: AsyncSession, *, endpoint: str | None, since: datetime) -> int:
    query = select(func.count()).select_from(OpenAIUsageEvent).where(OpenAIUsageEvent.created_at >= since)
    if endpoint:
        query = query.where(OpenAIUsageEvent.endpoint == endpoint)
    return int((await db.execute(query)).scalar_one())


async def reserve_openai_call(
    db: AsyncSession,
    *,
    endpoint: str,
    operation: str,
    model: str,
) -> OpenAIUsageEvent:
    """Reserve an explicit remote call before it is sent, enforcing request caps."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    checks = (
        ("OPENAI_DAILY_REQUEST_LIMIT", _limit("OPENAI_DAILY_REQUEST_LIMIT"), None, today),
        ("OPENAI_MONTHLY_REQUEST_LIMIT", _limit("OPENAI_MONTHLY_REQUEST_LIMIT"), None, month),
        (_endpoint_limit_name(endpoint), _limit(_endpoint_limit_name(endpoint)), endpoint, today),
    )
    for label, cap, scoped_endpoint, since in checks:
        if cap and await _count_since(db, endpoint=scoped_endpoint, since=since) >= cap:
            raise HTTPException(status_code=429, detail=f"openai_request_limit_reached:{label}")

    event = OpenAIUsageEvent(endpoint=endpoint, operation=operation, model=model, status="pending")
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


def _tokens(payload: dict[str, Any] | None) -> tuple[int | None, int | None]:
    usage = (payload or {}).get("usage") or {}
    input_tokens = usage.get("input_tokens", usage.get("prompt_tokens"))
    output_tokens = usage.get("output_tokens", usage.get("completion_tokens"))
    return (
        int(input_tokens) if isinstance(input_tokens, (int, float)) else None,
        int(output_tokens) if isinstance(output_tokens, (int, float)) else None,
    )


async def complete_openai_call(
    db: AsyncSession,
    event: OpenAIUsageEvent,
    *,
    succeeded: bool,
    payload: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    input_tokens, output_tokens = _tokens(payload)
    event.status = "success" if succeeded else "failed"
    event.input_tokens = input_tokens
    event.output_tokens = output_tokens
    event.error_message = error_message[:1000] if error_message else None
    event.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()


def configured_limits() -> dict[str, int]:
    return {
        "daily": _limit("OPENAI_DAILY_REQUEST_LIMIT"),
        "monthly": _limit("OPENAI_MONTHLY_REQUEST_LIMIT"),
        "news_summary_daily": _limit("OPENAI_NEWS_SUMMARY_DAILY_REQUEST_LIMIT"),
        "jarvis_daily": _limit("OPENAI_JARVIS_DAILY_REQUEST_LIMIT"),
        "semantic_search_daily": _limit("OPENAI_SEMANTIC_SEARCH_DAILY_REQUEST_LIMIT"),
    }
