from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.logging_config import get_logger
from backend.models import Store
from backend.orchestrator import AgentRunner, EventEmitter, StateMachine, WorkflowEngine
from backend.schemas import (
    AgentRunResponse,
    EventLogResponse,
    StoreResponse,
    TimelineResponse,
    WorkflowStatusResponse,
)
from backend.stores.agent_run import AgentRunStore
from backend.stores.event_log import EventLogStore
from backend.stores.store import StoreStore
from backend.stores.workflow import WorkflowStore

logger = get_logger(__name__)


class WorkflowService:
    def __init__(
        self,
        session: AsyncSession,
        store_store: StoreStore,
        workflow_store: WorkflowStore,
        agent_run_store: AgentRunStore,
        event_log_store: EventLogStore,
        state_machine: StateMachine,
        event_emitter: EventEmitter,
        agent_runner: AgentRunner,
    ) -> None:
        self._session = session
        self._store = store_store
        self._workflow = workflow_store
        self._agent_run = agent_run_store
        self._event_log = event_log_store
        self._state_machine = state_machine
        self._event_emitter = event_emitter
        self._agent_runner = agent_runner

    async def _require_store(self, store_id: int) -> Store:
        store = await self._store.get_by_id(store_id)
        if not store:
            raise HTTPException(status_code=404, detail="Store not found")
        return store

    async def get_store_detail(self, store_id: int) -> StoreResponse:
        store = await self._require_store(store_id)
        return StoreResponse.model_validate(store)

    async def get_status(self, store_id: int) -> WorkflowStatusResponse:
        store = await self._require_store(store_id)
        wf = await self._workflow.get_by_store_id(store_id)
        if not wf:
            raise HTTPException(status_code=404, detail="Workflow not found")
        recent = await self._agent_run.list_by_store(store_id, limit=10)
        return WorkflowStatusResponse(
            store_id=store.id,
            store_name=store.name,
            current_state=wf.current_state,
            consecutive_failures=wf.consecutive_failures,
            retry_count=wf.retry_count,
            started_at=wf.started_at,
            recent_agent_runs=[
                AgentRunResponse(
                    id=r.id,
                    agent_type=r.agent_type,
                    status=r.status,
                    state_at_run=r.state_at_run,
                    output_data=r.output_data or {},
                    error_msg=r.error_msg,
                    retry_count=r.retry_count,
                    duration_ms=r.duration_ms,
                    created_at=r.created_at,
                )
                for r in recent
            ],
        )

    async def get_timeline(self, store_id: int) -> TimelineResponse:
        store = await self._require_store(store_id)
        wf = await self._workflow.get_by_store_id(store_id)
        current_state = wf.current_state if wf else "NEW_STORE"
        events = await self._event_log.list_by_store(store_id, limit=100)
        return TimelineResponse(
            store_id=store.id,
            store_name=store.name,
            current_state=current_state,
            events=[
                EventLogResponse(
                    id=e.id,
                    event_type=e.event_type,
                    from_state=e.from_state,
                    to_state=e.to_state,
                    agent_type=e.agent_type,
                    message=e.message,
                    extra_data=e.extra_data or {},
                    created_at=e.created_at,
                )
                for e in events
            ],
        )

    async def start_workflow(self, store_id: int) -> dict[str, int | str]:
        from backend.database import AsyncSessionLocal

        store = await self._require_store(store_id)
        async with AsyncSessionLocal() as session:
            eng = WorkflowEngine(
                db=session,
                state_machine=self._state_machine,
                event_emitter=self._event_emitter,
                agent_runner=self._agent_runner,
            )
            try:
                await eng.run_workflow(store)
                await session.commit()
            except Exception as e:
                logger.error(
                    f"Workflow error for store {store_id}: {e}", exc_info=True
                )
                await session.rollback()
                raise
        return {"message": "Workflow started", "store_id": store_id}

    async def manual_takeover(self, store_id: int) -> dict[str, int | str]:
        store = await self._require_store(store_id)
        eng = WorkflowEngine(
            db=self._session,
            state_machine=self._state_machine,
            event_emitter=self._event_emitter,
            agent_runner=self._agent_runner,
        )
        await eng.trigger_manual_takeover(store)
        await self._session.commit()
        return {"message": "Manual takeover triggered", "store_id": store_id}