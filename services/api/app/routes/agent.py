from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentMemory, AgentTask, Article, ArticleAI, ArticleUserState, Briefing, Source
from app.db.session import get_db
from app.routes.sources import _recommendation_rank, _source_health_rows

router = APIRouter()


class AgentMemoryCreate(BaseModel):
    agent_id: str = Field(default="jarvis", min_length=1, max_length=80)
    memory_type: Literal["summary", "synthesis", "decision", "note", "briefing"] = "summary"
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=1)
    language: str = Field(default="fr", min_length=2, max_length=16)
    tags: list[str] = []
    source_article_ids: list[int] = []
    source_urls: list[str] = []
    confidence: float | None = Field(default=None, ge=0, le=1)
    metadata: dict[str, Any] = {}


class AgentTaskCreate(BaseModel):
    agent_id: str = Field(default="jarvis", min_length=1, max_length=80)
    task_type: Literal["synthesis", "briefing", "research", "source_maintenance", "watchlist", "custom"] = "synthesis"
    title: str = Field(min_length=1, max_length=240)
    instructions: str = Field(min_length=1)
    priority: int = Field(default=2, ge=1, le=4)
    language: str = Field(default="fr", min_length=2, max_length=16)
    input_payload: dict[str, Any] = {}
    source_article_ids: list[int] = []


class AgentTaskComplete(BaseModel):
    result_payload: dict[str, Any] = {}
    memory_id: int | None = None
    create_memory: AgentMemoryCreate | None = None


class AgentTaskFail(BaseModel):
    error_message: str = Field(min_length=1)
    result_payload: dict[str, Any] = {}


def _memory_payload(memory: AgentMemory) -> dict[str, Any]:
    return {
        "id": int(memory.id),
        "agent_id": memory.agent_id,
        "memory_type": memory.memory_type,
        "title": memory.title,
        "content": memory.content,
        "language": memory.language,
        "tags": memory.tags or [],
        "source_article_ids": [int(item) for item in (memory.source_article_ids or [])],
        "source_urls": memory.source_urls or [],
        "confidence": float(memory.confidence) if memory.confidence is not None else None,
        "metadata": memory.memory_metadata or {},
        "created_at": memory.created_at.isoformat() if memory.created_at else None,
        "updated_at": memory.updated_at.isoformat() if memory.updated_at else None,
    }


def _task_payload(task: AgentTask) -> dict[str, Any]:
    return {
        "id": int(task.id),
        "agent_id": task.agent_id,
        "task_type": task.task_type,
        "title": task.title,
        "instructions": task.instructions,
        "status": task.status,
        "priority": int(task.priority or 2),
        "language": task.language,
        "input_payload": task.input_payload or {},
        "result_payload": task.result_payload or {},
        "error_message": task.error_message,
        "source_article_ids": [int(item) for item in (task.source_article_ids or [])],
        "memory_id": int(task.memory_id) if task.memory_id is not None else None,
        "claimed_at": task.claimed_at.isoformat() if task.claimed_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "failed_at": task.failed_at.isoformat() if task.failed_at else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


async def _create_memory_from_payload(db: AsyncSession, payload: AgentMemoryCreate) -> AgentMemory:
    memory = AgentMemory(
        agent_id=payload.agent_id,
        memory_type=payload.memory_type,
        title=payload.title,
        content=payload.content,
        language=payload.language,
        tags=payload.tags,
        source_article_ids=payload.source_article_ids,
        source_urls=payload.source_urls,
        confidence=payload.confidence,
        memory_metadata=payload.metadata,
    )
    db.add(memory)
    await db.flush()
    return memory


async def _agent_articles(
    db: AsyncSession,
    *,
    profile_id: str,
    limit: int,
    mode: str,
    category: str | None,
    min_score: float | None,
) -> list[dict[str, Any]]:
    article_date = func.coalesce(Article.published_at, Article.discovered_at, Article.extracted_at).label("article_date")
    q = (
        select(
            Article.id,
            Article.title,
            Article.url,
            article_date,
            Article.word_count,
            Article.language,
            ArticleAI.summary_short,
            ArticleAI.summary_long,
            ArticleAI.category,
            ArticleAI.final_score,
            ArticleAI.entities,
            Source.name.label("source_name"),
            ArticleUserState.is_read,
            ArticleUserState.is_saved,
            ArticleUserState.is_hidden,
        )
        .outerjoin(ArticleAI, ArticleAI.article_id == Article.id)
        .outerjoin(Source, Source.id == Article.source_id)
        .outerjoin(
            ArticleUserState,
            and_(ArticleUserState.article_id == Article.id, ArticleUserState.profile_id == profile_id),
        )
    )
    if category:
        q = q.where(ArticleAI.category == category)
    if min_score is not None:
        q = q.where(ArticleAI.final_score >= min_score)
    q = q.where(or_(ArticleUserState.is_hidden.is_(False), ArticleUserState.is_hidden.is_(None)))

    if mode == "recent":
        q = q.order_by(desc(article_date))
    elif mode == "saved":
        q = q.where(ArticleUserState.is_saved.is_(True)).order_by(desc(article_date))
    else:
        q = q.order_by(desc(ArticleAI.final_score), desc(article_date))

    rows = (await db.execute(q.limit(limit))).all()
    return [
        {
            "id": int(row.id),
            "title": row.title,
            "url": row.url,
            "source": row.source_name,
            "published_at": row.article_date.isoformat() if row.article_date else None,
            "language": row.language,
            "category": row.category,
            "summary_short": row.summary_short,
            "summary_long": row.summary_long,
            "final_score": float(row.final_score or 0),
            "word_count": row.word_count,
            "entities": row.entities,
            "user_state": {
                "is_read": bool(row.is_read) if row.is_read is not None else False,
                "is_saved": bool(row.is_saved) if row.is_saved is not None else False,
                "is_hidden": bool(row.is_hidden) if row.is_hidden is not None else False,
            },
        }
        for row in rows
    ]


async def _latest_briefing(db: AsyncSession, category: str = "all") -> dict[str, Any] | None:
    briefing = (
        await db.execute(
            select(Briefing)
            .where(Briefing.category == category)
            .order_by(desc(Briefing.period_date), desc(Briefing.generated_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    if briefing is None and category != "all":
        briefing = (
            await db.execute(
                select(Briefing).order_by(desc(Briefing.period_date), desc(Briefing.generated_at)).limit(1)
            )
        ).scalar_one_or_none()
    if briefing is None:
        return None
    return {
        "id": int(briefing.id),
        "period": briefing.period,
        "period_date": briefing.period_date.isoformat() if briefing.period_date else None,
        "category": briefing.category,
        "content": briefing.content,
        "article_ids": [int(item) for item in (briefing.article_ids or [])],
        "cluster_ids": [int(item) for item in (briefing.cluster_ids or [])],
        "generated_at": briefing.generated_at.isoformat() if briefing.generated_at else None,
    }


async def _recent_memories(db: AsyncSession, agent_id: str, limit: int) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(AgentMemory)
            .where(AgentMemory.agent_id == agent_id)
            .order_by(desc(AgentMemory.created_at))
            .limit(limit)
        )
    ).scalars().all()
    return [_memory_payload(row) for row in rows]


async def _queued_tasks(db: AsyncSession, agent_id: str, limit: int) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(AgentTask)
            .where(AgentTask.agent_id == agent_id)
            .where(AgentTask.status == "queued")
            .order_by(AgentTask.priority.asc(), AgentTask.created_at.asc())
            .limit(limit)
        )
    ).scalars().all()
    return [_task_payload(row) for row in rows]


@router.get("/capabilities")
async def agent_capabilities():
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "service": "helix-agent-api",
        "version": "v1",
        "auth": "X-API-Token",
        "read": [
            "context",
            "top_articles",
            "latest_briefing",
            "source_recommendations",
            "memories",
            "tasks",
            "jarvis_query",
        ],
        "write": [
            "create_memory",
            "delete_memory",
            "create_task",
            "claim_task",
            "complete_task",
            "fail_task",
            "article_user_state",
            "source_actions",
        ],
        "recommended_client": "clients/python/helix_agent_client",
    }


@router.get("/context")
async def agent_context(
    agent_id: str = Query(default="jarvis", min_length=1, max_length=80),
    profile_id: str = Query(default="default"),
    mode: Literal["top", "recent", "saved"] = "top",
    language: str = Query(default="fr"),
    category: str | None = None,
    limit: int = Query(default=12, ge=1, le=50),
    min_score: float | None = Query(default=None, ge=0, le=1),
    include_source_recommendations: bool = True,
    db: AsyncSession = Depends(get_db),
):
    articles = await _agent_articles(
        db,
        profile_id=profile_id,
        limit=limit,
        mode=mode,
        category=category,
        min_score=min_score,
    )
    briefing = await _latest_briefing(db, category or "all")
    memories = await _recent_memories(db, agent_id, limit=5)
    tasks = await _queued_tasks(db, agent_id, limit=5)

    source_recommendations: list[dict[str, Any]] = []
    if include_source_recommendations:
        rows = await _source_health_rows(db)
        actionable = [
            row
            for row in rows
            if (row.get("recommendation") or {}).get("action") not in {"keep", "keep_disabled"}
        ]
        actionable.sort(key=_recommendation_rank)
        source_recommendations = actionable[:8]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agent_id": agent_id,
        "profile_id": profile_id,
        "language": language,
        "mode": mode,
        "contract": {
            "answer_style": "Concise, factual, cite source ids/urls when possible.",
            "writeback": "Store durable syntheses with POST /v1/agent/memories.",
            "limits": {"articles": limit, "recent_memories": 5, "queued_tasks": 5, "source_recommendations": 8},
        },
        "latest_briefing": briefing,
        "articles": articles,
        "source_recommendations": source_recommendations,
        "recent_memories": memories,
        "queued_tasks": tasks,
        "suggested_tasks": [
            "Summarize the highest scoring articles in French.",
            "Identify weak signals across source recommendations and recent articles.",
            "Store a synthesis if the user asks for a durable summary.",
        ],
    }


@router.post("/memories", status_code=201)
async def create_agent_memory(payload: AgentMemoryCreate, db: AsyncSession = Depends(get_db)):
    memory = await _create_memory_from_payload(db, payload)
    await db.commit()
    await db.refresh(memory)
    return _memory_payload(memory)


@router.get("/memories")
async def list_agent_memories(
    agent_id: str = Query(default="jarvis", min_length=1, max_length=80),
    memory_type: str | None = None,
    tag: str | None = None,
    limit: int = Query(default=30, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(AgentMemory).where(AgentMemory.agent_id == agent_id)
    if memory_type:
        q = q.where(AgentMemory.memory_type == memory_type)
    if tag:
        q = q.where(AgentMemory.tags.any(tag))
    rows = (await db.execute(q.order_by(desc(AgentMemory.created_at)).limit(limit))).scalars().all()
    return {"count": len(rows), "items": [_memory_payload(row) for row in rows]}


@router.get("/memories/{memory_id}")
async def get_agent_memory(memory_id: int, db: AsyncSession = Depends(get_db)):
    memory = await db.get(AgentMemory, memory_id)
    if memory is None:
        raise HTTPException(404, "Agent memory not found")
    return _memory_payload(memory)


@router.delete("/memories/{memory_id}", status_code=204)
async def delete_agent_memory(memory_id: int, db: AsyncSession = Depends(get_db)):
    memory = await db.get(AgentMemory, memory_id)
    if memory is None:
        raise HTTPException(404, "Agent memory not found")
    await db.delete(memory)
    await db.commit()


@router.post("/tasks", status_code=201)
async def create_agent_task(payload: AgentTaskCreate, db: AsyncSession = Depends(get_db)):
    task = AgentTask(
        agent_id=payload.agent_id,
        task_type=payload.task_type,
        title=payload.title,
        instructions=payload.instructions,
        priority=payload.priority,
        language=payload.language,
        input_payload=payload.input_payload,
        source_article_ids=payload.source_article_ids,
        status="queued",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return _task_payload(task)


@router.get("/tasks")
async def list_agent_tasks(
    agent_id: str = Query(default="jarvis", min_length=1, max_length=80),
    status: Literal["queued", "running", "done", "failed", "cancelled", "all"] = "queued",
    task_type: str | None = None,
    limit: int = Query(default=30, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(AgentTask).where(AgentTask.agent_id == agent_id)
    if status != "all":
        q = q.where(AgentTask.status == status)
    if task_type:
        q = q.where(AgentTask.task_type == task_type)
    rows = (
        await db.execute(
            q.order_by(AgentTask.priority.asc(), AgentTask.created_at.asc()).limit(limit)
        )
    ).scalars().all()
    return {"count": len(rows), "items": [_task_payload(row) for row in rows]}


@router.get("/tasks/{task_id}")
async def get_agent_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(AgentTask, task_id)
    if task is None:
        raise HTTPException(404, "Agent task not found")
    return _task_payload(task)


@router.post("/tasks/claim")
async def claim_next_agent_task(
    agent_id: str = Query(default="jarvis", min_length=1, max_length=80),
    task_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(AgentTask).where(AgentTask.agent_id == agent_id).where(AgentTask.status == "queued")
    if task_type:
        q = q.where(AgentTask.task_type == task_type)
    task = (
        await db.execute(
            q.order_by(AgentTask.priority.asc(), AgentTask.created_at.asc()).limit(1)
        )
    ).scalar_one_or_none()
    if task is None:
        return {"claimed": False, "task": None}
    task.status = "running"
    task.claimed_at = datetime.now(timezone.utc)
    task.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)
    return {"claimed": True, "task": _task_payload(task)}


@router.post("/tasks/{task_id}/complete")
async def complete_agent_task(task_id: int, payload: AgentTaskComplete, db: AsyncSession = Depends(get_db)):
    task = await db.get(AgentTask, task_id)
    if task is None:
        raise HTTPException(404, "Agent task not found")
    if task.status not in {"queued", "running"}:
        raise HTTPException(409, f"Task cannot be completed from status '{task.status}'")

    memory_id = payload.memory_id
    if payload.create_memory is not None:
        memory = await _create_memory_from_payload(db, payload.create_memory)
        memory_id = int(memory.id)

    task.status = "done"
    task.result_payload = payload.result_payload
    task.memory_id = memory_id
    task.error_message = None
    task.completed_at = datetime.now(timezone.utc)
    task.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)
    return _task_payload(task)


@router.post("/tasks/{task_id}/fail")
async def fail_agent_task(task_id: int, payload: AgentTaskFail, db: AsyncSession = Depends(get_db)):
    task = await db.get(AgentTask, task_id)
    if task is None:
        raise HTTPException(404, "Agent task not found")
    if task.status not in {"queued", "running"}:
        raise HTTPException(409, f"Task cannot be failed from status '{task.status}'")
    task.status = "failed"
    task.error_message = payload.error_message
    task.result_payload = payload.result_payload
    task.failed_at = datetime.now(timezone.utc)
    task.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)
    return _task_payload(task)


@router.post("/tasks/{task_id}/cancel")
async def cancel_agent_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(AgentTask, task_id)
    if task is None:
        raise HTTPException(404, "Agent task not found")
    if task.status in {"done", "failed", "cancelled"}:
        raise HTTPException(409, f"Task cannot be cancelled from status '{task.status}'")
    task.status = "cancelled"
    task.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)
    return _task_payload(task)
