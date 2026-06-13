from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProcessingLog
from app.db.session import get_db

router = APIRouter()

HA_WEBHOOK_URL = os.environ.get("HOME_ASSISTANT_WEBHOOK_URL", "").strip()
HA_WEBHOOK_TOKEN = os.environ.get("HOME_ASSISTANT_WEBHOOK_TOKEN", "").strip()


async def _deliver(event: str, payload: dict) -> tuple[bool, str]:
    if not HA_WEBHOOK_URL:
        return False, "HOME_ASSISTANT_WEBHOOK_URL not configured"

    headers = {"Content-Type": "application/json", "X-Helix-Event": event}
    if HA_WEBHOOK_TOKEN:
        headers["Authorization"] = f"Bearer {HA_WEBHOOK_TOKEN}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(HA_WEBHOOK_URL, headers=headers, json=payload)
            response.raise_for_status()
        return True, "delivered"
    except Exception as exc:
        return False, str(exc)


class BriefingReadyPayload(BaseModel):
    date: str
    category: str = "all"
    briefing_id: int | None = None
    message: str | None = None


class AlertPayload(BaseModel):
    alert_type: str = Field(min_length=1, max_length=120)
    severity: str = Field(default="warning", pattern="^(info|warning|critical)$")
    message: str = Field(min_length=1, max_length=2000)
    source: str | None = None


@router.post("/briefing-ready")
async def home_assistant_briefing_ready(payload: BriefingReadyPayload, db: AsyncSession = Depends(get_db)):
    outbound_payload = {
        "event": "briefing_ready",
        "date": payload.date,
        "category": payload.category,
        "briefing_id": payload.briefing_id,
        "message": payload.message,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    delivered, delivery_message = await _deliver("briefing_ready", outbound_payload)

    db.add(
        ProcessingLog(
            item_type="home_assistant",
            item_id=payload.briefing_id,
            step="briefing_ready",
            status="success" if delivered else "error",
            message=delivery_message,
            payload=outbound_payload,
        )
    )
    await db.commit()
    return {
        "accepted": delivered,
        "event": "briefing_ready",
        "message": delivery_message,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/alert")
async def home_assistant_alert(payload: AlertPayload, db: AsyncSession = Depends(get_db)):
    outbound_payload = {
        "event": "alert",
        "alert_type": payload.alert_type,
        "severity": payload.severity,
        "message": payload.message,
        "source": payload.source,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    delivered, delivery_message = await _deliver("alert", outbound_payload)

    db.add(
        ProcessingLog(
            item_type="home_assistant",
            step="alert",
            status="success" if delivered else "error",
            message=delivery_message,
            payload=outbound_payload,
        )
    )
    await db.commit()
    return {
        "accepted": delivered,
        "event": "alert",
        "severity": payload.severity,
        "message": delivery_message,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
