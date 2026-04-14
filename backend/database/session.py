from __future__ import annotations

import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./multi_agent_ops.db")

async_engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal: async_sessionmaker = async_sessionmaker(async_engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependency for FastAPI routes to get async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
