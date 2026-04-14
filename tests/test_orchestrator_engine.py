"""
Integration tests for the refactored WorkflowEngine.
Mocks StateMachine, EventEmitter, and AgentRunner to test the orchestrator layer.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.agents.base import AgentResult, AgentResultStatus
from backend.models._enums import WorkflowState
from backend.orchestrator.engine import WorkflowEngine


def _make_db():
    """Build a mock async database session."""
    db = MagicMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


def _make_runner(results: dict[str, AgentResult]):
    """Build a mock AgentRunner that returns predefined results."""
    runner = MagicMock()
    for agent_type, result in results.items():
        runner.run = AsyncMock(return_value=({"store_id": "test"}, result))
    runner.store_to_dict = MagicMock(return_value={"store_id": "test", "name": "Test Store"})
    return runner


def _make_sm(initial_state: WorkflowState = WorkflowState.NEW_STORE):
    """Build a mock StateMachine with a controllable workflow instance."""
    wf = MagicMock()
    wf.current_state = initial_state.value
    wf.consecutive_failures = 0
    wf.flush = AsyncMock()
    wf.add = MagicMock()
    sm = MagicMock()
    sm.get_or_create_workflow = AsyncMock(return_value=wf)
    sm.get_agents_for_state = MagicMock(return_value=["analyzer"])
    sm.get_next_state = MagicMock(return_value=WorkflowState.DIAGNOSIS)
    sm.transition = AsyncMock()
    sm.trigger_manual_takeover = AsyncMock(return_value=wf)
    return sm, wf


def _make_emitter():
    """Build a mock EventEmitter."""
    emitter = MagicMock()
    emitter.log_event = AsyncMock()
    emitter.create_alert = AsyncMock()
    return emitter


class TestWorkflowEngineIntegration:
    """Test WorkflowEngine orchestration by mocking sub-components."""

    @pytest.mark.asyncio
    async def test_engine_passes_correct_state_to_sm(self):
        sm, wf = _make_sm(WorkflowState.DIAGNOSIS)
        runner = _make_runner({"analyzer": AgentResult(agent_type="analyzer", status=AgentResultStatus.SUCCESS)})
        emitter = _make_emitter()

        engine = WorkflowEngine(db=_make_db(), state_machine=sm, event_emitter=emitter, agent_runner=runner)
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        await engine.run_workflow(store)

        sm.get_agents_for_state.assert_called_once_with(WorkflowState.DIAGNOSIS)

    @pytest.mark.asyncio
    async def test_engine_calls_runner_for_each_agent(self):
        sm, wf = _make_sm(WorkflowState.DAILY_OPS)
        sm.get_agents_for_state = MagicMock(return_value=["web_operator", "mobile_operator"])

        results = {
            "web_operator": AgentResult(agent_type="web_operator", status=AgentResultStatus.SUCCESS),
            "mobile_operator": AgentResult(agent_type="mobile_operator", status=AgentResultStatus.SUCCESS),
        }
        runner = _make_runner(results)
        emitter = _make_emitter()

        engine = WorkflowEngine(db=_make_db(), state_machine=sm, event_emitter=emitter, agent_runner=runner)
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        await engine.run_workflow(store)

        assert runner.run.call_count == 2

    @pytest.mark.asyncio
    async def test_engine_stops_on_agent_failure(self):
        sm, wf = _make_sm(WorkflowState.DIAGNOSIS)
        runner = _make_runner({"analyzer": AgentResult(agent_type="analyzer", status=AgentResultStatus.FAILED, error="oops")})
        emitter = _make_emitter()

        engine = WorkflowEngine(db=_make_db(), state_machine=sm, event_emitter=emitter, agent_runner=runner)
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        await engine.run_workflow(store)

        # Should only call run once (stops after first failure)
        assert runner.run.call_count == 1

    @pytest.mark.asyncio
    async def test_engine_triggers_manual_review_after_max_failures(self):
        sm, wf = _make_sm(WorkflowState.DIAGNOSIS)
        wf.consecutive_failures = 2  # Already 2 failures

        runner = _make_runner({"analyzer": AgentResult(agent_type="analyzer", status=AgentResultStatus.FAILED)})
        emitter = _make_emitter()

        engine = WorkflowEngine(db=_make_db(), state_machine=sm, event_emitter=emitter, agent_runner=runner)
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        await engine.run_workflow(store)

        # Should emit critical alert
        emitter.create_alert.assert_called()
        alert_call = emitter.create_alert.call_args
        assert alert_call.kwargs["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_engine_transitions_on_success(self):
        sm, wf = _make_sm(WorkflowState.DIAGNOSIS)
        sm.get_next_state = MagicMock(return_value=WorkflowState.FOUNDATION)
        runner = _make_runner({"analyzer": AgentResult(agent_type="analyzer", status=AgentResultStatus.SUCCESS)})
        emitter = _make_emitter()

        engine = WorkflowEngine(db=_make_db(), state_machine=sm, event_emitter=emitter, agent_runner=runner)
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        await engine.run_workflow(store)

        sm.transition.assert_called_once()
        transition_call = sm.transition.call_args
        assert transition_call[0][3] == WorkflowState.DIAGNOSIS
        assert transition_call[0][4] == WorkflowState.FOUNDATION

    @pytest.mark.asyncio
    async def test_engine_skips_done_state(self):
        sm, wf = _make_sm(WorkflowState.DONE)
        runner = _make_runner({})
        emitter = _make_emitter()

        engine = WorkflowEngine(db=_make_db(), state_machine=sm, event_emitter=emitter, agent_runner=runner)
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        result_wf = await engine.run_workflow(store)

        # Should not try to run any agents
        runner.run.assert_not_called()
        assert result_wf is wf

    @pytest.mark.asyncio
    async def test_manual_takeover_calls_sm_and_emitter(self):
        sm, wf = _make_sm(WorkflowState.DAILY_OPS)
        emitter = _make_emitter()
        engine = WorkflowEngine(db=_make_db(), state_machine=sm, event_emitter=emitter, agent_runner=MagicMock())
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        await engine.trigger_manual_takeover(store)

        sm.trigger_manual_takeover.assert_called_once()
        emitter.log_event.assert_called()
        emitter.create_alert.assert_called()
