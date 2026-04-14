"""
Integration tests for the store-based WorkflowEngine.
Mocks stores, StateMachine, EventEmitter, and AgentRunner.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.agents.base import AgentResult, AgentResultStatus
from backend.models._enums import WorkflowState
from backend.orchestrator.engine import WorkflowEngine


def _make_runner(results: dict[str, AgentResult]):
    """Build a mock AgentRunner that returns predefined results."""
    runner = MagicMock()
    for agent_type, result in results.items():
        runner.run = AsyncMock(return_value=({"store_id": "test"}, result))
    runner.store_to_dict = MagicMock(return_value={"store_id": "test", "name": "Test Store"})
    return runner


def _make_wf_store(initial_state: WorkflowState = WorkflowState.NEW_STORE):
    """Build a mock WorkflowStore with a controllable workflow instance."""
    wf = MagicMock()
    wf.current_state = initial_state.value
    wf.consecutive_failures = 0
    wf.store_id = 1

    wf_store = MagicMock()
    wf_store.get_or_create_workflow = AsyncMock(return_value=wf)
    wf_store.transition_workflow = AsyncMock()
    wf_store.trigger_manual_takeover = AsyncMock(return_value=wf)
    wf_store.update_timestamp = AsyncMock()
    return wf_store, wf


def _make_agent_run_store():
    """Build a mock AgentRunStore."""
    ar_store = MagicMock()
    run = MagicMock()
    run.id = 5
    ar_store.create_agent_run = AsyncMock(return_value=run)
    return ar_store


def _make_report_store():
    """Build a mock ReportStore."""
    rp_store = MagicMock()
    report = MagicMock()
    report.id = 10
    rp_store.create_report = AsyncMock(return_value=report)
    return rp_store


def _make_emitter():
    """Build a mock EventEmitter."""
    emitter = MagicMock()
    emitter.emit_event = MagicMock()
    emitter.emit_alert = MagicMock()
    return emitter


@pytest.mark.asyncio
class TestWorkflowEngineIntegration:
    """Test WorkflowEngine orchestration with mocked stores and components."""

    async def test_engine_passes_correct_state_to_sm(self):
        wf_store, wf = _make_wf_store(WorkflowState.DIAGNOSIS)
        ar_store = _make_agent_run_store()
        rp_store = _make_report_store()

        sm = MagicMock()
        sm.get_agents_for_state = MagicMock(return_value=["analyzer"])

        runner = _make_runner({"analyzer": AgentResult(agent_type="analyzer", status=AgentResultStatus.SUCCESS)})
        emitter = _make_emitter()

        engine = WorkflowEngine(
            workflow_store=wf_store,
            agent_run_store=ar_store,
            report_store=rp_store,
            state_machine=sm,
            event_emitter=emitter,
            agent_runner=runner,
        )
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        await engine.run_workflow(store)

        sm.get_agents_for_state.assert_called_once_with(WorkflowState.DIAGNOSIS)

    async def test_engine_calls_runner_for_each_agent(self):
        wf_store, wf = _make_wf_store(WorkflowState.DAILY_OPS)
        ar_store = _make_agent_run_store()
        rp_store = _make_report_store()

        sm = MagicMock()
        sm.get_agents_for_state = MagicMock(return_value=["web_operator", "mobile_operator"])

        results = {
            "web_operator": AgentResult(agent_type="web_operator", status=AgentResultStatus.SUCCESS),
            "mobile_operator": AgentResult(agent_type="mobile_operator", status=AgentResultStatus.SUCCESS),
        }
        runner = _make_runner(results)
        emitter = _make_emitter()

        engine = WorkflowEngine(
            workflow_store=wf_store,
            agent_run_store=ar_store,
            report_store=rp_store,
            state_machine=sm,
            event_emitter=emitter,
            agent_runner=runner,
        )
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        await engine.run_workflow(store)

        assert runner.run.call_count == 2

    async def test_engine_stops_on_agent_failure(self):
        wf_store, wf = _make_wf_store(WorkflowState.DIAGNOSIS)
        ar_store = _make_agent_run_store()
        rp_store = _make_report_store()

        sm = MagicMock()
        sm.get_agents_for_state = MagicMock(return_value=["analyzer"])

        runner = _make_runner({"analyzer": AgentResult(agent_type="analyzer", status=AgentResultStatus.FAILED, error="oops")})
        emitter = _make_emitter()

        engine = WorkflowEngine(
            workflow_store=wf_store,
            agent_run_store=ar_store,
            report_store=rp_store,
            state_machine=sm,
            event_emitter=emitter,
            agent_runner=runner,
        )
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        await engine.run_workflow(store)

        # Should only call run once (stops after first failure)
        assert runner.run.call_count == 1

    async def test_engine_triggers_manual_review_after_max_failures(self):
        wf_store, wf = _make_wf_store(WorkflowState.DIAGNOSIS)
        wf.consecutive_failures = 2  # Already 2 failures
        ar_store = _make_agent_run_store()
        rp_store = _make_report_store()

        sm = MagicMock()
        sm.get_agents_for_state = MagicMock(return_value=["analyzer"])

        runner = _make_runner({"analyzer": AgentResult(agent_type="analyzer", status=AgentResultStatus.FAILED)})
        emitter = _make_emitter()

        engine = WorkflowEngine(
            workflow_store=wf_store,
            agent_run_store=ar_store,
            report_store=rp_store,
            state_machine=sm,
            event_emitter=emitter,
            agent_runner=runner,
        )
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        await engine.run_workflow(store)

        # Should emit critical alert
        emitter.emit_alert.assert_called()
        alert_call = emitter.emit_alert.call_args
        assert alert_call[0][0].severity == "critical"

    async def test_engine_transitions_on_success(self):
        wf_store, wf = _make_wf_store(WorkflowState.DIAGNOSIS)
        ar_store = _make_agent_run_store()
        rp_store = _make_report_store()

        sm = MagicMock()
        sm.get_agents_for_state = MagicMock(return_value=["analyzer"])
        sm.get_next_state = MagicMock(return_value=WorkflowState.FOUNDATION)

        runner = _make_runner({"analyzer": AgentResult(agent_type="analyzer", status=AgentResultStatus.SUCCESS)})
        emitter = _make_emitter()

        engine = WorkflowEngine(
            workflow_store=wf_store,
            agent_run_store=ar_store,
            report_store=rp_store,
            state_machine=sm,
            event_emitter=emitter,
            agent_runner=runner,
        )
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        await engine.run_workflow(store)

        wf_store.transition_workflow.assert_called_once()
        transition_call = wf_store.transition_workflow.call_args
        assert transition_call[0][1] == WorkflowState.DIAGNOSIS
        assert transition_call[0][2] == WorkflowState.FOUNDATION

    async def test_engine_skips_done_state(self):
        wf_store, wf = _make_wf_store(WorkflowState.DONE)
        ar_store = _make_agent_run_store()
        rp_store = _make_report_store()

        sm = MagicMock()
        sm.get_agents_for_state = MagicMock(return_value=[])

        runner = _make_runner({})
        emitter = _make_emitter()

        engine = WorkflowEngine(
            workflow_store=wf_store,
            agent_run_store=ar_store,
            report_store=rp_store,
            state_machine=sm,
            event_emitter=emitter,
            agent_runner=runner,
        )
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        result_wf = await engine.run_workflow(store)

        # Should not try to run any agents
        runner.run.assert_not_called()
        assert result_wf is wf

    async def test_manual_takeover_calls_wf_and_emitter(self):
        wf_store, wf = _make_wf_store(WorkflowState.DAILY_OPS)
        ar_store = _make_agent_run_store()
        rp_store = _make_report_store()

        sm = MagicMock()
        emitter = _make_emitter()
        runner = MagicMock()

        engine = WorkflowEngine(
            workflow_store=wf_store,
            agent_run_store=ar_store,
            report_store=rp_store,
            state_machine=sm,
            event_emitter=emitter,
            agent_runner=runner,
        )
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        await engine.trigger_manual_takeover(store)

        wf_store.trigger_manual_takeover.assert_called_once()
        emitter.emit_event.assert_called()
        emitter.emit_alert.assert_called()
