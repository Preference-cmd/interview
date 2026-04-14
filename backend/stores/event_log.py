from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import EventLog


class EventLogStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_store(
        self, store_id: int, limit: int = 100
    ) -> list[EventLog]:
        stmt = (
            select(EventLog)
            .where(EventLog.store_id == store_id)
            .order_by(EventLog.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
