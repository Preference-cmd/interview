from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.base import AgentResult, AgentResultStatus
from backend.database.session import AsyncSessionLocal
from backend.logging_config import get_logger
from backend.models import Alert, EventLog, Store, WorkflowInstance, WorkflowState
from backend.orchestrator.agent_runner import AgentRunner
from backend.orchestrator.event_emitter import EventEmitter
from backend.orchestrator.state_machine import StateMachine
from backend.stores.agent_run import AgentRunStore
from backend.stores.report import ReportStore
from backend.stores.store import StoreStore
from backend.stores.workflow import WorkflowStore

logger = get_logger(__name__)


class WorkflowEngine:
    """
    Orchestrates the multi-agent workflow for a single store.
    Entry point that coordinates StateMachine, EventEmitter, AgentRunner, and stores.
    """

    MAX_RETRIES = 3

    def __init__(
        self,
        workflow_store: WorkflowStore,
        agent_run_store: AgentRunStore,
        report_store: ReportStore,
        state_machine: StateMachine,
        event_emitter: EventEmitter,
        agent_runner: AgentRunner,
    ) -> None:
        self._wf = workflow_store
        self._agent_run = agent_run_store
        self._report = report_store
        self.sm = state_machine
        self.emitter = event_emitter
        self.runner = agent_runner

    async def get_or_create_workflow(self, store: Store) -> WorkflowInstance:
        return await self._wf.get_or_create_workflow(store.id)

    async def run_workflow(self, store: Store) -> WorkflowInstance:
        """Run a single workflow step (one state). Kept for backward compatibility."""
        wf = await self._wf.get_or_create_workflow(store.id)
        state = WorkflowState(wf.current_state)

        logger.info(f"Starting workflow for store {store.store_id}, state={state.value}")

        if state == WorkflowState.DONE:
            logger.info("Store already DONE, skipping")
            return wf

        await self._run_single_state(store, wf, state)
        await self._wf.update_timestamp(wf)
        return wf

    async def _run_single_state(
        self,
        store: Store,
        wf: WorkflowInstance,
        state: WorkflowState,
    ) -> WorkflowState:
        """
        Run all agents for the given state, handle failures and transitions,
        return the next state.
        """
        agents_to_run = self.sm.get_agents_for_state(state)

        context: dict = {
            "store_id": store.store_id,
            "store_data": self.runner.store_to_dict(store),
            "workflow_state": state.value,
        }

        any_failure = False

        for agent_type in agents_to_run:
            context, result = await self.runner.run(
                agent_type, context, max_retries=self.MAX_RETRIES
            )
            await self._persist_agent_run(store.id, agent_type, context, result, state)

            if result.status != AgentResultStatus.SUCCESS:
                any_failure = True
                break

        if any_failure:
            wf.consecutive_failures += 1
            if wf.consecutive_failures >= self.MAX_RETRIES:
                next_state = WorkflowState.MANUAL_REVIEW
                alert = Alert(
                    store_id=store.id,
                    alert_type="consecutive_failure",
                    severity="critical",
                    message=f"连续{self.MAX_RETRIES}次失败，触发人工接管",
                    extra_data={"failures": wf.consecutive_failures},
                )
                self.emitter.emit_alert(alert)
                logger.warning(
                    f"Store {store.store_id}: consecutive failures "
                    f"{wf.consecutive_failures} -> MANUAL_REVIEW"
                )
            else:
                next_state = state
                logger.warning(
                    f"Store {store.store_id}: failure in {state.value}, "
                    f"retry {wf.consecutive_failures}/{self.MAX_RETRIES - 1}"
                )
        else:
            wf.consecutive_failures = 0
            next_state = self.sm.get_next_state(state)
            logger.info(
                f"Store {store.store_id}: {state.value} completed, "
                f"transitioning to {next_state.value}"
            )

        if next_state != state:
            await self._wf.transition_workflow(wf, state, next_state)
            event = EventLog(
                store_id=store.id,
                event_type="state_change",
                from_state=state.value,
                to_state=next_state.value,
                message=f"State transition: {state.value} -> {next_state.value}",
            )
            self.emitter.emit_event(event)

        if next_state == WorkflowState.WEEKLY_REPORT:
            await self._generate_report(store, context, "weekly")

        return next_state

    async def run_workflow_loop(
        self,
        store_id: int,
        delay_seconds: float = 3.0,
    ) -> WorkflowInstance:
        """
        Run workflow continuously through all states.
        Creates its own AsyncSession so it survives across HTTP requests.
        """
        async with AsyncSessionLocal() as session:
            store_store = StoreStore(session)
            wf_store = WorkflowStore(session)
            ar_store = AgentRunStore(session)
            rp_store = ReportStore(session)

            # Build a fresh engine for this session
            engine = _build_loop_engine(session, store_store, wf_store, ar_store, rp_store)

            # Re-fetch store and workflow with this session
            store = await store_store.get_by_id(store_id)
            if not store:
                logger.error(f"Store {store_id} not found")
                return None

            wf = await wf_store.get_or_create_workflow(store.id)

            while True:
                state = WorkflowState(wf.current_state)

                if state in (WorkflowState.DONE, WorkflowState.MANUAL_REVIEW):
                    break

                # Mark as running
                wf.is_running = True
                session.add(wf)
                await session.flush()

                logger.info(f"Loop: running state {state.value} for store {store.store_id}")

                try:
                    next_state = await engine._run_single_state(store, wf, state)
                except Exception:
                    wf.is_running = False
                    session.add(wf)
                    await session.commit()
                    raise

                # Persist after each step
                await wf_store.update_timestamp(wf)
                wf.is_running = False
                session.add(wf)
                await session.commit()

                # Check if terminal state reached
                if next_state in (WorkflowState.DONE, WorkflowState.MANUAL_REVIEW):
                    logger.info(
                        f"Loop: terminal state {next_state.value} reached for "
                        f"store {store.store_id}"
                    )
                    break

                try:
                    await asyncio.sleep(delay_seconds)
                except asyncio.CancelledError:
                    logger.info(f"Loop: cancelled for store {store.store_id}")
                    # Mark not running on cancellation
                    wf.is_running = False
                    session.add(wf)
                    await session.commit()
                    raise

        return wf

    async def _persist_agent_run(
        self,
        store_id: int,
        agent_type: str,
        context: dict,
        result: AgentResult,
        state: WorkflowState,
    ) -> None:
        retry_count = getattr(result, "attempts", 1) - 1

        run = await self._agent_run.create_agent_run(
            store_id=store_id,
            agent_type=agent_type,
            status=result.status.value,
            state_at_run=state.value,
            input_data={"store_data": context.get("store_data", {})},
            output_data=result.data or {},
            error_msg=result.error,
            retry_count=retry_count,
            duration_ms=result.duration_ms,
        )

        event = EventLog(
            store_id=store_id,
            event_type="agent_run",
            agent_type=agent_type,
            message=f"{agent_type} {result.status.value} ({result.duration_ms}ms)",
            extra_data={"run_id": run.id, "error": result.error},
        )
        self.emitter.emit_event(event)

    async def _generate_report(self, store: Store, context: dict, report_type: str) -> None:
        report_context: dict = {
            **context,
            "store_id": store.store_id,
            "store_data": self.runner.store_to_dict(store),
            "report_type": report_type,
        }

        _, result = await self.runner.run("reporter", report_context)

        if result.status == AgentResultStatus.SUCCESS:
            report = await self._report.create_report(
                store_id=store.id,
                report_type=report_type,
                content_md=result.data.get("md_report"),
                content_json=result.data.get("json_report"),
            )
            event = EventLog(
                store_id=store.id,
                event_type="report_generated",
                message=f"{report_type} report generated",
                extra_data={"report_id": report.id},
            )
            self.emitter.emit_event(event)
            logger.info(f"Report generated for store {store.store_id}")

    async def trigger_manual_takeover(self, store: Store) -> WorkflowInstance:
        wf = await self._wf.get_or_create_workflow(store.id)
        old_state = WorkflowState(wf.current_state)

        await self._wf.trigger_manual_takeover(wf)

        self.emitter.emit_event(
            EventLog(
                store_id=store.id,
                event_type="manual_takeover",
                from_state=old_state.value,
                to_state=WorkflowState.MANUAL_REVIEW.value,
                message="Manual takeover triggered",
            )
        )
        self.emitter.emit_alert(
            Alert(
                store_id=store.id,
                alert_type="manual_takeover",
                severity="warning",
                message="人工接管已触发",
            )
        )
        logger.info(f"Manual takeover triggered for store {store.store_id}")
        return wf


def _build_loop_engine(
    session: AsyncSession,
    store_store: StoreStore,
    wf_store: WorkflowStore,
    ar_store: AgentRunStore,
    rp_store: ReportStore,
) -> WorkflowEngine:
    """Build a WorkflowEngine with session-owned stores for use in run_workflow_loop."""
    from backend.orchestrator import AgentRunner, EventEmitter, StateMachine

    agents = {
        "analyzer": _get_agent("analyzer"),
        "web_operator": _get_agent("web_operator"),
        "mobile_operator": _get_agent("mobile_operator"),
        "reporter": _get_agent("reporter"),
    }
    return WorkflowEngine(
        workflow_store=wf_store,
        agent_run_store=ar_store,
        report_store=rp_store,
        state_machine=StateMachine(),
        event_emitter=EventEmitter(session),
        agent_runner=AgentRunner(agents),
    )


def _get_agent(name: str):
    """Lazy-load agent to avoid circular imports."""
    if name == "analyzer":
        from backend.agents.analyzer import AnalyzerAgent

        return AnalyzerAgent()
    elif name == "web_operator":
        from backend.agents.web_operator import WebOperatorAgent

        return WebOperatorAgent(failure_rate=0.2)
    elif name == "mobile_operator":
        from backend.agents.mobile_operator import MobileOperatorAgent

        return MobileOperatorAgent(failure_rate=0.25)
    elif name == "reporter":
        from backend.agents.reporter import ReporterAgent

        return ReporterAgent()
    raise ValueError(f"Unknown agent: {name}")
