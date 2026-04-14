from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.logging_config import get_logger
from backend.models import VALID_TRANSITIONS, Store, WorkflowInstance, WorkflowState

logger = get_logger(__name__)


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

    async def create_workflow(self, store_id: int) -> WorkflowInstance:
        """Create a new workflow instance for a store."""
        wf = WorkflowInstance(
            store_id=store_id,
            current_state=WorkflowState.NEW_STORE.value,
            consecutive_failures=0,
            retry_count=0,
            started_at=datetime.now(UTC),
        )
        self._session.add(wf)
        await self._session.flush()
        return wf

    async def get_or_create_workflow(self, store_id: int) -> WorkflowInstance:
        """Get existing workflow or create a new one."""
        wf = await self.get_by_store_id(store_id)
        if wf is None:
            wf = await self.create_workflow(store_id)
        return wf

    async def transition_workflow(
        self,
        wf: WorkflowInstance,
        from_state: WorkflowState,
        to_state: WorkflowState,
    ) -> None:
        """Transition workflow to a new state with validation."""
        valid = VALID_TRANSITIONS.get(from_state, set())
        if to_state not in valid:
            logger.error(f"Invalid transition: {from_state.value} -> {to_state.value}")
            return

        wf.current_state = to_state.value
        self._session.add(wf)
        await self._session.flush()
        logger.info(f"Store {wf.store_id}: transitioned {from_state.value} -> {to_state.value}")

    async def trigger_manual_takeover(self, wf: WorkflowInstance) -> WorkflowInstance:
        """Move a workflow to MANUAL_REVIEW state."""
        wf.current_state = WorkflowState.MANUAL_REVIEW.value
        wf.consecutive_failures = 0
        wf.updated_at = datetime.now(UTC)
        self._session.add(wf)
        await self._session.flush()
        logger.info(f"Manual takeover triggered for store {wf.store_id}")
        return wf

    async def update_timestamp(self, wf: WorkflowInstance) -> None:
        """Update workflow updated_at timestamp."""
        wf.updated_at = datetime.now(UTC)
        self._session.add(wf)
        await self._session.flush()
