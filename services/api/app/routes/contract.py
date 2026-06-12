from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserFeedback, UserProfile
from app.db.session import get_db

router = APIRouter()


class ProfileUpsertPayload(BaseModel):
    profile_id: str = Field(min_length=1, max_length=120)
    interests: list[str] = []
    muted_sources: list[str] = []
    languages: list[str] = []
    metadata: dict = {}


class FeedbackPayload(BaseModel):
    profile_id: str = Field(min_length=1, max_length=120)
    article_id: int
    signal: str = Field(pattern="^(useful|not_useful|saved)$")
    value: int = Field(default=0, ge=-100, le=100)
    context: dict = {}


@router.post("/profiles/upsert")
async def upsert_profile(payload: ProfileUpsertPayload, db: AsyncSession = Depends(get_db)):
    profile = (
        await db.execute(select(UserProfile).where(UserProfile.profile_id == payload.profile_id))
    ).scalar_one_or_none()

    if profile is None:
        profile = UserProfile(profile_id=payload.profile_id)
        db.add(profile)

    profile.interests = payload.interests
    profile.muted_sources = payload.muted_sources
    profile.languages = payload.languages
    profile.metadata = payload.metadata

    await db.commit()
    await db.refresh(profile)

    return {
        "profile_id": profile.profile_id,
        "interests": profile.interests or [],
        "muted_sources": profile.muted_sources or [],
        "languages": profile.languages or [],
        "metadata": profile.metadata or {},
    }


@router.get("/profiles/{profile_id}")
async def get_profile(profile_id: str, db: AsyncSession = Depends(get_db)):
    profile = (
        await db.execute(select(UserProfile).where(UserProfile.profile_id == profile_id))
    ).scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {
        "profile_id": profile.profile_id,
        "interests": profile.interests or [],
        "muted_sources": profile.muted_sources or [],
        "languages": profile.languages or [],
        "metadata": profile.metadata or {},
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


@router.post("/feedback")
async def write_feedback(payload: FeedbackPayload, db: AsyncSession = Depends(get_db)):
    row = UserFeedback(
        profile_id=payload.profile_id,
        article_id=payload.article_id,
        signal=payload.signal,
        value=payload.value,
        context=payload.context,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {
        "id": row.id,
        "profile_id": row.profile_id,
        "article_id": row.article_id,
        "signal": row.signal,
        "value": row.value,
    }


@router.get("/feedback/{profile_id}")
async def list_feedback(profile_id: str, limit: int = 50, db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(UserFeedback)
            .where(UserFeedback.profile_id == profile_id)
            .order_by(desc(UserFeedback.created_at))
            .limit(max(1, min(limit, 500)))
        )
    ).scalars().all()
    return {
        "profile_id": profile_id,
        "count": len(rows),
        "items": [
            {
                "id": r.id,
                "article_id": r.article_id,
                "signal": r.signal,
                "value": r.value,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }
