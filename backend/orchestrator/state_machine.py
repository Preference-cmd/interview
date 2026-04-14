from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.logging_config import get_logger
from backend.models import (
    VALID_TRANSITIONS,
    Store,
    WorkflowInstance,
    WorkflowState,
)

logger = get_logger(__name__)


class StateMachine:
    """
    Manages workflow state transitions and agent-to-state mappings.
    """

    STATES_REQUIRING_ANALYZER = {WorkflowState.DIAGNOSIS}
    STATES_REQUIRING_WEB_OPS = {WorkflowState.FOUNDATION, WorkflowState.DAILY_OPS}
    STATES_REQUIRING_MOBILE_OPS = {WorkflowState.DAILY_OPS}
    STATES_REQUIRING_REPORTER = {WorkflowState.WEEKLY_REPORT}

    def get_agents_for_state(self, state: WorkflowState) -> list[str]:
        agents: list[str] = []
        if state in self.STATES_REQUIRING_ANALYZER:
            agents.append("analyzer")
        if state in self.STATES_REQUIRING_WEB_OPS:
            agents.append("web_operator")
        if state in self.STATES_REQUIRING_MOBILE_OPS:
            agents.append("mobile_operator")
        if state in self.STATES_REQUIRING_REPORTER:
            agents.append("reporter")
        return agents

    def get_next_state(self, current: WorkflowState) -> WorkflowState:
        next_map: dict[WorkflowState, WorkflowState] = {
            WorkflowState.NEW_STORE: WorkflowState.DIAGNOSIS,
            WorkflowState.DIAGNOSIS: WorkflowState.FOUNDATION,
            WorkflowState.FOUNDATION: WorkflowState.DAILY_OPS,
            WorkflowState.DAILY_OPS: WorkflowState.WEEKLY_REPORT,
            WorkflowState.WEEKLY_REPORT: WorkflowState.DONE,
        }
        return next_map.get(current, current)

    def is_valid_transition(self, from_: WorkflowState, to: WorkflowState) -> bool:
        return to in VALID_TRANSITIONS.get(from_, set())

    async def get_or_create_workflow(
        self, db: AsyncSession, store: Store
    ) -> WorkflowInstance:
        """Get existing workflow or create a new one for the store."""
        stmt = select(WorkflowInstance).where(WorkflowInstance.store_id == store.id)
        result = await db.execute(stmt)
        wf = result.scalar_one_or_none()
        if wf is None:
            wf = WorkflowInstance(
                store_id=store.id,
                current_state=WorkflowState.NEW_STORE.value,
                consecutive_failures=0,
                retry_count=0,
                started_at=datetime.now(UTC),
            )
            db.add(wf)
            await db.flush()
            logger.info(f"Created workflow for store {store.store_id}")
        return wf

    async def transition(
        self,
        db: AsyncSession,
        store_id: int,
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
        db.add(wf)
        await db.flush()
        logger.info(f"Store {store_id}: transitioned {from_state.value} -> {to_state.value}")

    async def trigger_manual_takeover(
        self, db: AsyncSession, store: Store
    ) -> WorkflowInstance:
        """Move a store to MANUAL_REVIEW state."""
        wf = await self.get_or_create_workflow(db, store)
        _old_state = WorkflowState(wf.current_state)

        wf.current_state = WorkflowState.MANUAL_REVIEW.value
        wf.consecutive_failures = 0
        wf.updated_at = datetime.now(UTC)
        db.add(wf)
        await db.flush()

        logger.info(f"Manual takeover triggered for store {store.store_id}")
        return wf
