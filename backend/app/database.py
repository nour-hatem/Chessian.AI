"""Async database engine and session factory."""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from typing import AsyncGenerator

from app.config import settings
from app.models import Base

# Async engine — uses asyncpg driver
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields an async database session.

    Routers are responsible for calling ``await db.commit()`` explicitly.
    This dependency only handles rollback on unhandled errors.

    Usage:
        @router.get("/example")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
            await db.commit()
    """
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def create_tables():
    """Create all tables (dev only — use Alembic in production)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all tables (dev/testing only)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
