from __future__ import annotations

from datetime import UTC, datetime

from backend.agents.base import AgentResult, AgentResultStatus
from backend.logging_config import get_logger
from backend.models import AgentRun, Report, Store, WorkflowInstance, WorkflowState
from backend.orchestrator.agent_runner import AgentRunner
from backend.orchestrator.event_emitter import EventEmitter
from backend.orchestrator.state_machine import StateMachine

logger = get_logger(__name__)


class WorkflowEngine:
    """
    Orchestrates the multi-agent workflow for a single store.
    Entry point that coordinates StateMachine, EventEmitter, and AgentRunner.
    """

    MAX_RETRIES = 3

    def __init__(
        self,
        db,
        state_machine: StateMachine,
        event_emitter: EventEmitter,
        agent_runner: AgentRunner,
    ) -> None:
        self.db = db
        self.sm = state_machine
        self.emitter = event_emitter
        self.runner = agent_runner

    async def get_or_create_workflow(self, store: Store) -> WorkflowInstance:
        """Delegate to StateMachine."""
        return await self.sm.get_or_create_workflow(self.db, store)

    async def run_workflow(self, store: Store) -> WorkflowInstance:
        """
        Execute the full workflow for a store.
        Runs agents based on current state, handles transitions, and manages failures.
        """
        wf = await self.sm.get_or_create_workflow(self.db, store)
        state = WorkflowState(wf.current_state)

        logger.info(f"Starting workflow for store {store.store_id}, state={state.value}")

        if state == WorkflowState.DONE:
            logger.info("Store already DONE, skipping")
            return wf

        # Determine which agents to run in this state
        agents_to_run = self.sm.get_agents_for_state(state)

        # Build initial context
        context: dict = {
            "store_id": store.store_id,
            "store_data": self.runner.store_to_dict(store),
            "workflow_state": state.value,
        }

        # Run agents and collect results
        any_failure = False

        for agent_type in agents_to_run:
            context, result = await self.runner.run(
                agent_type, context, max_retries=self.MAX_RETRIES
            )
            await self._persist_agent_run(store.id, agent_type, context, result, state)

            if result.status != AgentResultStatus.SUCCESS:
                any_failure = True
                break

        # Determine next state
        if any_failure:
            wf.consecutive_failures += 1
            if wf.consecutive_failures >= self.MAX_RETRIES:
                next_state = WorkflowState.MANUAL_REVIEW
                await self.emitter.create_alert(
                    db=self.db,
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
            next_state = self.sm.get_next_state(state)
            logger.info(
                f"Store {store.store_id}: {state.value} completed, "
                f"transitioning to {next_state.value}"
            )

        # Transition state
        if next_state != state:
            await self.sm.transition(self.db, store.id, wf, state, next_state)
            await self.emitter.log_event(
                db=self.db,
                store_id=store.id,
                event_type="state_change",
                from_state=state.value,
                to_state=next_state.value,
                message=f"State transition: {state.value} -> {next_state.value}",
            )

        # Generate report if entering WEEKLY_REPORT
        if next_state == WorkflowState.WEEKLY_REPORT:
            await self._generate_report(store, context, "weekly")

        wf.updated_at = datetime.now(UTC)
        self.db.add(wf)
        await self.db.flush()
        return wf

    async def _persist_agent_run(
        self,
        store_id: int,
        agent_type: str,
        context: dict,
        result: AgentResult,
        state: WorkflowState,
    ) -> None:
        """Persist an agent run record."""
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

        await self.emitter.log_event(
            db=self.db,
            store_id=store_id,
            event_type="agent_run",
            agent_type=agent_type,
            message=f"{agent_type} {result.status.value} ({result.duration_ms}ms)",
            extra_data={"run_id": run.id, "error": result.error},
        )

    async def _generate_report(self, store: Store, context: dict, report_type: str) -> None:
        """Generate and persist a report."""
        report_context: dict = {
            **context,
            "store_id": store.store_id,
            "store_data": self.runner.store_to_dict(store),
            "report_type": report_type,
        }

        _, result = await self.runner.run("reporter", report_context)

        if result.status == AgentResultStatus.SUCCESS:
            report = Report(
                store_id=store.id,
                report_type=report_type,
                content_md=result.data.get("md_report"),
                content_json=result.data.get("json_report"),
            )
            self.db.add(report)
            await self.db.flush()
            await self.emitter.log_event(
                db=self.db,
                store_id=store.id,
                event_type="report_generated",
                message=f"{report_type} report generated",
                extra_data={"report_id": report.id},
            )
            logger.info(f"Report generated for store {store.store_id}")

    async def trigger_manual_takeover(self, store: Store) -> WorkflowInstance:
        """Move a store to MANUAL_REVIEW state."""
        wf = await self.sm.trigger_manual_takeover(self.db, store)
        old_state = WorkflowState(wf.current_state)

        await self.emitter.log_event(
            db=self.db,
            store_id=store.id,
            event_type="manual_takeover",
            from_state=old_state.value,
            to_state=WorkflowState.MANUAL_REVIEW.value,
            message="Manual takeover triggered",
        )
        await self.emitter.create_alert(
            db=self.db,
            store_id=store.id,
            alert_type="manual_takeover",
            severity="warning",
            message="人工接管已触发",
        )
        logger.info(f"Manual takeover triggered for store {store.store_id}")
        return wf
