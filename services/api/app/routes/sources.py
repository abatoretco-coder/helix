from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Source
from app.schemas.sources import SourceRead, SourceCreate, SourceUpdate

router = APIRouter()


@router.get("/", response_model=list[SourceRead])
async def list_sources(
    enabled: Optional[bool] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Source).order_by(Source.priority, Source.name)
    if enabled is not None:
        q = q.where(Source.enabled == enabled)
    if category:
        q = q.where(Source.category == category)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{source_id}", response_model=SourceRead)
async def get_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    return source


@router.post("/", response_model=SourceRead, status_code=201)
async def create_source(payload: SourceCreate, db: AsyncSession = Depends(get_db)):
    source = Source(**payload.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.patch("/{source_id}", response_model=SourceRead)
async def update_source(source_id: int, payload: SourceUpdate, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    await db.commit()
    await db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=204)
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    await db.delete(source)
    await db.commit()
