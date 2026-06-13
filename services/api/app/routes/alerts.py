from __future__ import annotations

from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AlertRule, NotificationChannel, ProcessingLog
from app.db.session import get_db

router = APIRouter()


class NotificationChannelPayload(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    channel_type: str = Field(pattern="^(home_assistant|webhook)$")
    target_url: str = Field(min_length=1, max_length=2000)
    auth_token: str | None = None
    config: dict | None = None
    enabled: bool = True


class AlertRulePayload(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    event_type: str = Field(min_length=1, max_length=120)
    channel_id: int
    config: dict | None = None
    enabled: bool = True


class DispatchPayload(BaseModel):
    event_type: str = Field(min_length=1, max_length=120)
    severity: str = Field(default="warning", pattern="^(info|warning|critical)$")
    message: str = Field(min_length=1, max_length=2000)
    payload: dict | None = None


@router.get("/channels")
async def list_channels(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(NotificationChannel).order_by(NotificationChannel.id.desc()))).scalars().all()
    return {
        "count": len(rows),
        "items": [
            {
                "id": int(row.id),
                "name": row.name,
                "channel_type": row.channel_type,
                "target_url": row.target_url,
                "enabled": bool(row.enabled),
                "config": row.channel_config or {},
            }
            for row in rows
        ],
    }


@router.post("/channels")
async def create_channel(payload: NotificationChannelPayload, db: AsyncSession = Depends(get_db)):
    row = NotificationChannel(
        name=payload.name,
        channel_type=payload.channel_type,
        target_url=payload.target_url,
        auth_token=payload.auth_token,
        channel_config=payload.config or {},
        enabled=payload.enabled,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"id": int(row.id), "name": row.name}


@router.get("/rules")
async def list_rules(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(AlertRule).order_by(AlertRule.id.desc()))).scalars().all()
    return {
        "count": len(rows),
        "items": [
            {
                "id": int(row.id),
                "name": row.name,
                "event_type": row.event_type,
                "channel_id": int(row.channel_id) if row.channel_id is not None else None,
                "enabled": bool(row.enabled),
                "config": row.rule_config or {},
            }
            for row in rows
        ],
    }


@router.post("/rules")
async def create_rule(payload: AlertRulePayload, db: AsyncSession = Depends(get_db)):
    channel = await db.get(NotificationChannel, payload.channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")

    row = AlertRule(
        name=payload.name,
        event_type=payload.event_type,
        channel_id=payload.channel_id,
        rule_config=payload.config or {},
        enabled=payload.enabled,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"id": int(row.id), "name": row.name}


@router.post("/dispatch")
async def dispatch_alert(payload: DispatchPayload, db: AsyncSession = Depends(get_db)):
    rules = (
        await db.execute(
            select(AlertRule, NotificationChannel)
            .join(NotificationChannel, NotificationChannel.id == AlertRule.channel_id)
            .where(AlertRule.enabled.is_(True))
            .where(NotificationChannel.enabled.is_(True))
            .where(AlertRule.event_type == payload.event_type)
        )
    ).all()

    delivered = 0
    failed = 0
    for rule, channel in rules:
        body = {
            "event_type": payload.event_type,
            "severity": payload.severity,
            "message": payload.message,
            "rule": {"id": int(rule.id), "name": rule.name},
            "payload": payload.payload or {},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        headers = {"Content-Type": "application/json"}
        if channel.auth_token:
            headers["Authorization"] = f"Bearer {channel.auth_token}"

        status = "success"
        message = "delivered"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(channel.target_url, headers=headers, json=body)
                response.raise_for_status()
            delivered += 1
        except Exception as exc:
            failed += 1
            status = "error"
            message = str(exc)

        db.add(
            ProcessingLog(
                item_type="alert",
                item_id=int(rule.id),
                step="dispatch",
                status=status,
                message=message,
                payload={"channel_id": int(channel.id), "event_type": payload.event_type, "severity": payload.severity},
            )
        )

    await db.commit()
    return {
        "event_type": payload.event_type,
        "matched_rules": len(rules),
        "delivered": delivered,
        "failed": failed,
    }
