"""Async PostgreSQL connection and session lifecycle."""

import logging
from collections.abc import AsyncGenerator

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.config import settings
from backend.models import Base

logger = logging.getLogger("veilbench.database")


class Database:
    """Owns the database engine used by session-management routes."""

    def __init__(self) -> None:
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def available(self) -> bool:
        return self.session_factory is not None

    async def start(self) -> None:
        if not settings.DATABASE_URL:
            logger.warning("Database is not configured; session-management routes are disabled")
            return

        engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            if settings.DATABASE_AUTO_CREATE:
                if settings.ENVIRONMENT.lower() == "production":
                    raise RuntimeError("Production schema must be managed with Alembic migrations")
                async with engine.begin() as connection:
                    await connection.run_sync(Base.metadata.create_all)
        except (SQLAlchemyError, RuntimeError):
            await engine.dispose()
            if settings.ENVIRONMENT.lower() == "production":
                raise
            logger.exception("Database is unavailable; session-management routes are disabled")
            return

        self.engine = engine
        self.session_factory = async_sessionmaker(engine, expire_on_commit=False)
        logger.info("Session metadata database connected")

    async def stop(self) -> None:
        if self.engine is not None:
            await self.engine.dispose()
        self.engine = None
        self.session_factory = None

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        if self.session_factory is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session storage is not available",
            )
        async with self.session_factory() as session:
            yield session


database = Database()


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in database.get_session():
        yield session
