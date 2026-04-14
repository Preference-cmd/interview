from __future__ import annotations

import asyncio

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.logging_config import get_logger
from backend.models import Store, WorkflowState
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
from backend.stores.report import ReportStore
from backend.stores.store import StoreStore
from backend.stores.workflow import WorkflowStore

logger = get_logger(__name__)


async def _run_loop_background(store_id: int, delay_seconds: float) -> None:
    """Background task entry point — creates a standalone engine for the loop."""
    try:
        eng = WorkflowEngine(
            workflow_store=WorkflowStore(None),
            agent_run_store=AgentRunStore(None),
            report_store=ReportStore(None),
            state_machine=StateMachine(),
            event_emitter=EventEmitter(None),
            agent_runner=_build_agents(),
        )
        wf = await eng.run_workflow_loop(store_id, delay_seconds)
        logger.info(
            f"Background loop finished for store {store_id}, "
            f"final state={wf.current_state if wf else 'unknown'}"
        )
    except asyncio.CancelledError:
        logger.info(f"Background loop cancelled for store {store_id}")
        raise
    except Exception as e:
        logger.error(f"Background loop error for store {store_id}: {e}", exc_info=True)


def _build_agents() -> AgentRunner:
    """Build agent runner with all agent types for background tasks."""
    from backend.agents.analyzer import AnalyzerAgent
    from backend.agents.mobile_operator import MobileOperatorAgent
    from backend.agents.reporter import ReporterAgent
    from backend.agents.web_operator import WebOperatorAgent

    agents = {
        "analyzer": AnalyzerAgent(),
        "web_operator": WebOperatorAgent(failure_rate=0.2),
        "mobile_operator": MobileOperatorAgent(failure_rate=0.25),
        "reporter": ReporterAgent(),
    }
    return AgentRunner(agents)


class WorkflowService:
    def __init__(
        self,
        session: AsyncSession,
        store_store: StoreStore,
        workflow_store: WorkflowStore,
        agent_run_store: AgentRunStore,
        event_log_store: EventLogStore,
        report_store: ReportStore,
        state_machine: StateMachine,
        event_emitter: EventEmitter,
        agent_runner: AgentRunner,
    ) -> None:
        self._session = session
        self._store = store_store
        self._workflow = workflow_store
        self._agent_run = agent_run_store
        self._event_log = event_log_store
        self._report = report_store
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
            is_running=wf.is_running,
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

    async def start_workflow(
        self,
        store_id: int,
        delay_seconds: float = 3.0,
        force_restart: bool = False,
    ) -> dict[str, int | str | bool]:
        await self._require_store(store_id)

        # Check terminal state
        wf = await self._workflow.get_by_store_id(store_id)
        if wf and wf.current_state in (
            WorkflowState.DONE.value,
            WorkflowState.MANUAL_REVIEW.value,
        ):
            return {
                "message": "Workflow already terminal",
                "store_id": store_id,
                "is_running": False,
            }

        return {
            "message": "Workflow started in background",
            "store_id": store_id,
            "is_running": True,
        }

    async def start_workflow_loop(
        self,
        store_id: int,
        delay_seconds: float = 3.0,
        force_restart: bool = False,
        task_registry: dict[int, asyncio.Task] | None = None,
    ) -> dict[str, int | str | bool]:
        """
        Spawn a background task that runs the workflow loop.
        Returns immediately with task status.
        """
        store = await self._require_store(store_id)

        # Check terminal state
        wf = await self._workflow.get_by_store_id(store_id)
        if wf and wf.current_state in (
            WorkflowState.DONE.value,
            WorkflowState.MANUAL_REVIEW.value,
        ):
            return {
                "message": "Workflow already terminal",
                "store_id": store_id,
                "is_running": False,
            }

        registry = task_registry or {}

        # Cancel existing task if force_restart
        if store.id in registry:
            existing = registry[store.id]
            if not existing.done():
                if force_restart:
                    existing.cancel()
                    logger.info(f"Force-restart: cancelled existing loop for store {store_id}")
                else:
                    return {
                        "message": "Workflow already running",
                        "store_id": store_id,
                        "is_running": True,
                    }
            # Clean up done tasks
            del registry[store.id]

        # Spawn background task
        loop = asyncio.get_running_loop()
        task = loop.create_task(_run_loop_background(store.id, delay_seconds))
        registry[store.id] = task

        logger.info(
            f"Spawned background loop for store {store_id} "
            f"(delay={delay_seconds}s, force_restart={force_restart})"
        )
        return {
            "message": "Workflow started in background",
            "store_id": store_id,
            "is_running": True,
        }

    async def stop_workflow(
        self,
        store_id: int,
        task_registry: dict[int, asyncio.Task] | None = None,
    ) -> dict[str, int | str | bool]:
        """Cancel a running workflow loop for the given store."""
        store = await self._require_store(store_id)
        registry = task_registry or {}

        task = registry.get(store.id)
        if task and not task.done():
            task.cancel()
            del registry[store.id]
            logger.info(f"Stopped workflow loop for store {store_id}")
            return {
                "message": "Workflow stopped",
                "store_id": store_id,
                "is_running": False,
            }
        return {
            "message": "No running workflow",
            "store_id": store_id,
            "is_running": False,
        }

    async def manual_takeover(self, store_id: int) -> dict[str, int | str]:
        store = await self._require_store(store_id)
        eng = WorkflowEngine(
            workflow_store=self._workflow,
            agent_run_store=self._agent_run,
            report_store=self._report,
            state_machine=self._state_machine,
            event_emitter=self._event_emitter,
            agent_runner=self._agent_runner,
        )
        await eng.trigger_manual_takeover(store)
        await self._session.commit()
        return {"message": "Manual takeover triggered", "store_id": store_id}
