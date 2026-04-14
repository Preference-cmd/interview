from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import AgentRun, Store


class AgentRunStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_recent(
        self, store_id: int | None = None, limit: int = 20
    ) -> list[tuple[AgentRun, Store]]:
        stmt = (
            select(AgentRun, Store)
            .join(Store, AgentRun.store_id == Store.id)
            .order_by(AgentRun.created_at.desc())
            .limit(limit)
        )
        if store_id is not None:
            stmt = stmt.where(AgentRun.store_id == store_id)
        result = await self._session.execute(stmt)
        return list(result.all())

    async def list_by_store(self, store_id: int, limit: int = 10) -> list[AgentRun]:
        stmt = (
            select(AgentRun)
            .where(AgentRun.store_id == store_id)
            .order_by(AgentRun.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
