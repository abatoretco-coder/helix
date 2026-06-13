from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProcessingLog
from app.db.session import get_db

router = APIRouter()


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
    db.add(
        ProcessingLog(
            item_type="home_assistant",
            item_id=payload.briefing_id,
            step="briefing_ready",
            status="success",
            message=payload.message or f"briefing ready for {payload.date} ({payload.category})",
            payload=payload.model_dump(),
        )
    )
    await db.commit()
    return {
        "accepted": True,
        "event": "briefing_ready",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/alert")
async def home_assistant_alert(payload: AlertPayload, db: AsyncSession = Depends(get_db)):
    db.add(
        ProcessingLog(
            item_type="home_assistant",
            step="alert",
            status="success",
            message=payload.message,
            payload=payload.model_dump(),
        )
    )
    await db.commit()
    return {
        "accepted": True,
        "event": "alert",
        "severity": payload.severity,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
