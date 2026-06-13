from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Briefing
from app.queue import enqueue
from app.schemas.briefings import BriefingRead

router = APIRouter()


@router.get("/daily", response_model=BriefingRead)
async def get_daily_briefing(
    for_date: Optional[date] = None,
    category: str = "all",
    db: AsyncSession = Depends(get_db),
):
    target = for_date or date.today()
    q = select(Briefing).where(
        and_(
            Briefing.period == "daily",
            func.date(Briefing.period_date) == target,
            Briefing.category == category,
        )
    )
    result = await db.execute(q)
    briefing = result.scalar_one_or_none()
    if not briefing:
        raise HTTPException(404, f"No briefing for {target}. POST /briefings/generate to create one.")
    return briefing


@router.post("/generate", status_code=202)
async def generate_briefing(
    period: str = "daily",
    category: str = "all",
    for_date: Optional[date] = None,
):
    """Trigger async briefing generation via the AI worker."""
    target = for_date or date.today()
    payload = f"{period}:{target.isoformat()}:{category}"
    await enqueue("briefing", payload)
    return {"queued": payload}


@router.get("/", response_model=list[BriefingRead])
async def list_briefings(
    period: str = "daily",
    limit: int = Query(7, le=30),
    db: AsyncSession = Depends(get_db),
):
    q = select(Briefing).where(Briefing.period == period).order_by(desc(Briefing.period_date)).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()
