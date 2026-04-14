from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Store, WorkflowInstance, WorkflowState


class WorkflowStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_store_id(self, store_id: int) -> WorkflowInstance | None:
        stmt = select(WorkflowInstance).where(
            WorkflowInstance.store_id == store_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_state_distribution(self) -> dict[str, int]:
        stmt = select(WorkflowInstance)
        result = await self._session.execute(stmt)
        dist: dict[str, int] = {}
        for wf in result.scalars().all():
            dist[wf.current_state] = dist.get(wf.current_state, 0) + 1
        return dist

    async def get_manual_review_queue(
        self,
    ) -> list[tuple[WorkflowInstance, Store]]:
        stmt = (
            select(WorkflowInstance, Store)
            .join(Store, WorkflowInstance.store_id == Store.id)
            .where(WorkflowInstance.current_state == WorkflowState.MANUAL_REVIEW.value)
        )
        result = await self._session.execute(stmt)
        return list(result.all())
