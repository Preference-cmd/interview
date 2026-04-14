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

    async def create_agent_run(
        self,
        store_id: int,
        agent_type: str,
        status: str,
        state_at_run: str,
        input_data: dict,
        output_data: dict,
        error_msg: str | None,
        retry_count: int,
        duration_ms: int,
    ) -> AgentRun:
        """Create and persist an agent run record."""
        run = AgentRun(
            store_id=store_id,
            agent_type=agent_type,
            status=status,
            state_at_run=state_at_run,
            input_data=input_data,
            output_data=output_data,
            error_msg=error_msg,
            retry_count=retry_count,
            duration_ms=duration_ms,
        )
        self._session.add(run)
        await self._session.flush()
        return run
