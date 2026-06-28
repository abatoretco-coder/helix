import os
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    """Called at startup; creates tables if they don't exist yet (dev only)."""
    # In production the schema is created by init_db.sql via Docker init script.
    # This is a safety net for bare metal / dev runs.
    async with engine.begin() as conn:
        is_postgres = engine.url.get_backend_name().startswith("postgresql")
        if is_postgres:
            await conn.execute(text("SELECT pg_advisory_lock(29417531)"))
        try:
            await conn.run_sync(Base.metadata.create_all)
        finally:
            if is_postgres:
                await conn.execute(text("SELECT pg_advisory_unlock(29417531)"))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
