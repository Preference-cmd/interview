from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.analyzer import AnalyzerAgent
from backend.agents.base import AgentResult
from backend.agents.base import AgentStatus as AgentResultStatus
from backend.agents.mobile_operator import MobileOperatorAgent
from backend.agents.reporter import ReporterAgent
from backend.agents.web_operator import WebOperatorAgent
from backend.logging_config import get_logger
from backend.models import (
    VALID_TRANSITIONS,
    AgentRun,
    Alert,
    EventLog,
    Report,
    Store,
    WorkflowInstance,
    WorkflowState,
)

logger = get_logger(__name__)


class WorkflowEngine:
    """
    Orchestrates the multi-agent workflow for a single store.
    Handles state transitions, agent execution, retry logic, and event logging.
    """

    MAX_RETRIES = 3
    STATES_REQUIRING_ANALYZER = {WorkflowState.DIAGNOSIS}
    STATES_REQUIRING_WEB_OPS = {WorkflowState.FOUNDATION, WorkflowState.DAILY_OPS}
    STATES_REQUIRING_MOBILE_OPS = {WorkflowState.DAILY_OPS}
    STATES_REQUIRING_REPORTER = {WorkflowState.WEEKLY_REPORT}

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.analyzer = AnalyzerAgent()
        self.web_operator = WebOperatorAgent(failure_rate=0.2)
        self.mobile_operator = MobileOperatorAgent(failure_rate=0.25)
        self.reporter = ReporterAgent()

    async def get_or_create_workflow(self, store: Store) -> WorkflowInstance:
        """Get existing workflow or create a new one for the store."""
        stmt = select(WorkflowInstance).where(WorkflowInstance.store_id == store.id)
        result = await self.db.execute(stmt)
        wf = result.scalar_one_or_none()
        if wf is None:
            wf = WorkflowInstance(
                store_id=store.id,
                current_state=WorkflowState.NEW_STORE.value,
                consecutive_failures=0,
                retry_count=0,
                started_at=datetime.now(UTC),
            )
            self.db.add(wf)
            await self.db.flush()
            await self._log_event(
                store_id=store.id,
                event_type="workflow_created",
                message=f"Workflow created for store {store.store_id}",
                extra_data={"initial_state": wf.current_state},
            )
            logger.info(f"Created workflow for store {store.store_id}")
        return wf

    async def run_workflow(self, store: Store) -> WorkflowInstance:
        """
        Execute the full workflow for a store.
        Runs agents based on current state, handles transitions, and manages failures.
        """
        wf = await self.get_or_create_workflow(store)
        state = WorkflowState(wf.current_state)

        logger.info(f"Starting workflow for store {store.store_id}, state={state.value}")

        if state == WorkflowState.DONE:
            logger.info("Store already DONE, skipping")
            return wf

        # Determine which agents to run in this state
        agents_to_run = self._get_agents_for_state(state)

        # Build context
        context: dict = {
            "store_id": store.store_id,
            "store_data": self._store_to_dict(store),
            "workflow_state": state.value,
        }

        # Run agents and collect results
        any_failure = False

        for agent_type in agents_to_run:
            context, result = await self._run_agent(agent_type, context, wf)
            # Persist: pass actual retry count from result
            await self._persist_agent_run(store.id, agent_type, context, result, state)

            if result.status != AgentResultStatus.SUCCESS:
                any_failure = True
                break

        # Determine next state
        if any_failure:
            wf.consecutive_failures += 1
            if wf.consecutive_failures >= self.MAX_RETRIES:
                next_state = WorkflowState.MANUAL_REVIEW
                await self._create_alert(
                    store_id=store.id,
                    alert_type="consecutive_failure",
                    severity="critical",
                    message=f"连续{self.MAX_RETRIES}次失败，触发人工接管",
                    extra_data={"failures": wf.consecutive_failures},
                )
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
            next_state = self._get_next_state(state)
            logger.info(
                f"Store {store.store_id}: {state.value} completed, "
                f"transitioning to {next_state.value}"
            )

        # Transition state
        if next_state != state:
            await self._transition_state(store.id, wf, state, next_state)

        # Generate report if entering WEEKLY_REPORT
        if next_state == WorkflowState.WEEKLY_REPORT:
            await self._generate_report(store, context, "weekly")

        wf.updated_at = datetime.now(UTC)
        self.db.add(wf)
        await self.db.flush()
        return wf

    async def _run_agent(
        self, agent_type: str, context: dict, wf: WorkflowInstance
    ) -> tuple[dict, AgentResult]:
        """Run a specific agent with context."""
        agent_map: dict[
            str, AnalyzerAgent | MobileOperatorAgent | ReporterAgent | WebOperatorAgent
        ] = {
            "analyzer": self.analyzer,
            "web_operator": self.web_operator,
            "mobile_operator": self.mobile_operator,
            "reporter": self.reporter,
        }

        agent = agent_map.get(agent_type)
        if agent is None:
            return context, AgentResult(
                agent_type=agent_type,
                status=AgentResultStatus.FAILED,
                error=f"Unknown agent type: {agent_type}",
            )

        logger.info(f"Running agent {agent_type} for {context.get('store_id')}")

        # Agent's own failure_rate is injected at construction
        result = await agent.run_with_retry(
            context,
            max_retries=self.MAX_RETRIES,
        )

        # Update context with agent output
        if result.data:
            context[agent_type] = result.data
            if agent_type == "analyzer":
                context["diagnosis"] = result.data

        return context, result

    def _get_agents_for_state(self, state: WorkflowState) -> list[str]:
        """Return list of agent types to run for a given state."""
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

    def _get_next_state(self, current: WorkflowState) -> WorkflowState:
        """Get the next state in the happy path."""
        next_map: dict[WorkflowState, WorkflowState] = {
            WorkflowState.NEW_STORE: WorkflowState.DIAGNOSIS,
            WorkflowState.DIAGNOSIS: WorkflowState.FOUNDATION,
            WorkflowState.FOUNDATION: WorkflowState.DAILY_OPS,
            WorkflowState.DAILY_OPS: WorkflowState.WEEKLY_REPORT,
            WorkflowState.WEEKLY_REPORT: WorkflowState.DONE,
        }
        return next_map.get(current, current)

    async def _transition_state(
        self,
        store_id: int,
        wf: WorkflowInstance,
        from_state: WorkflowState,
        to_state: WorkflowState,
    ) -> None:
        """Transition workflow to a new state with validation."""
        valid = VALID_TRANSITIONS.get(from_state, set())
        if to_state not in valid and to_state != WorkflowState.MANUAL_REVIEW:
            logger.error(f"Invalid transition: {from_state.value} -> {to_state.value}")
            return

        old_state = wf.current_state
        wf.current_state = to_state.value
        self.db.add(wf)
        await self.db.flush()

        await self._log_event(
            store_id=store_id,
            event_type="state_change",
            from_state=from_state.value,
            to_state=to_state.value,
            message=f"State transition: {old_state} -> {to_state.value}",
        )
        logger.info(f"Store {store_id}: transitioned {from_state.value} -> {to_state.value}")

    async def _generate_report(self, store: Store, context: dict, report_type: str) -> None:
        """Generate and persist a report."""
        report_context: dict = {
            **context,
            "store_id": store.store_id,
            "store_data": self._store_to_dict(store),
            "report_type": report_type,
        }

        result = await self.reporter.execute(report_context)

        if result.status == AgentResultStatus.SUCCESS:
            report = Report(
                store_id=store.id,
                report_type=report_type,
                content_md=result.data.get("md_report"),
                content_json=result.data.get("json_report"),
            )
            self.db.add(report)
            await self.db.flush()
            await self._log_event(
                store_id=store.id,
                event_type="report_generated",
                message=f"{report_type} report generated",
                extra_data={"report_id": report.id},
            )
            logger.info(f"Report generated for store {store.store_id}")

    async def _persist_agent_run(
        self,
        store_id: int,
        agent_type: str,
        context: dict,
        result: AgentResult,
        state: WorkflowState,
    ) -> None:
        """Persist an agent run record."""
        # retry_count = attempts - 1 (attempts includes the final attempt)
        retry_count = getattr(result, "attempts", 1) - 1

        run = AgentRun(
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
        self.db.add(run)
        await self.db.flush()

        await self._log_event(
            store_id=store_id,
            event_type="agent_run",
            agent_type=agent_type,
            message=f"{agent_type} {result.status.value} ({result.duration_ms}ms)",
            extra_data={"run_id": run.id, "error": result.error},
        )

    async def _log_event(
        self,
        store_id: int,
        event_type: str,
        from_state: str | None = None,
        to_state: str | None = None,
        agent_type: str | None = None,
        message: str | None = None,
        extra_data: dict | None = None,
    ) -> None:
        """Create a structured event log entry."""
        event = EventLog(
            store_id=store_id,
            event_type=event_type,
            from_state=from_state,
            to_state=to_state,
            agent_type=agent_type,
            message=message,
            extra_data=extra_data or {},
        )
        self.db.add(event)

    async def _create_alert(
        self,
        store_id: int,
        alert_type: str,
        severity: str,
        message: str,
        extra_data: dict | None = None,
    ) -> None:
        """Create an alert for anomalies."""
        alert = Alert(
            store_id=store_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            extra_data=extra_data or {},
        )
        self.db.add(alert)

    async def trigger_manual_takeover(self, store: Store) -> WorkflowInstance:
        """Move a store to MANUAL_REVIEW state."""
        wf = await self.get_or_create_workflow(store)
        old_state = WorkflowState(wf.current_state)

        wf.current_state = WorkflowState.MANUAL_REVIEW.value
        wf.consecutive_failures = 0
        wf.updated_at = datetime.now(UTC)
        self.db.add(wf)
        await self.db.flush()

        await self._log_event(
            store_id=store.id,
            event_type="manual_takeover",
            from_state=old_state.value,
            to_state=WorkflowState.MANUAL_REVIEW.value,
            message="Manual takeover triggered",
        )
        await self._create_alert(
            store_id=store.id,
            alert_type="manual_takeover",
            severity="warning",
            message="人工接管已触发",
        )
        logger.info(f"Manual takeover triggered for store {store.store_id}")
        return wf

    def _store_to_dict(self, store: Store) -> dict:
        """Convert Store model to dict for agents."""
        return {
            "store_id": store.store_id,
            "name": store.name,
            "city": store.city,
            "category": store.category,
            "rating": store.rating,
            "monthly_orders": store.monthly_orders,
            "gmv_last_7d": store.gmv_last_7d,
            "review_count": store.review_count,
            "review_reply_rate": store.review_reply_rate,
            "ros_health": store.ros_health,
            "competitor_avg_discount": store.competitor_avg_discount,
            "issues": store.issues or [],
        }
