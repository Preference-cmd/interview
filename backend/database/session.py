from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./multi_agent_ops.db")

async_engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal: async_sessionmaker = async_sessionmaker(async_engine, expire_on_commit=False)
