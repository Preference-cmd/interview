"""
Integration tests for auto state transition (background loop).
Tests WorkflowEngine.run_workflow_loop and WorkflowService loop spawning.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agents.base import AgentResult, AgentResultStatus
from backend.models._enums import WorkflowState
from backend.orchestrator.engine import WorkflowEngine
from backend.service.workflow import WorkflowService


def _make_runner_success(all_agents: list[str]):
    """Build a mock AgentRunner that returns SUCCESS for all agents."""
    runner = MagicMock()
    runner.store_to_dict = MagicMock(return_value={"store_id": "test", "name": "Test"})
    for agent_type in all_agents:
        runner.run = AsyncMock(
            return_value=(
                {"store_id": "test"},
                AgentResult(agent_type=agent_type, status=AgentResultStatus.SUCCESS),
            )
        )
    return runner


def _make_wf_store(initial_state: WorkflowState = WorkflowState.NEW_STORE):
    """Build a mock WorkflowStore with a controllable workflow instance."""
    wf = MagicMock()
    wf.current_state = initial_state.value
    wf.consecutive_failures = 0
    wf.retry_count = 0
    wf.is_running = False
    wf.store_id = 1

    wf_store = MagicMock()
    wf_store.get_or_create_workflow = AsyncMock(return_value=wf)
    wf_store.transition_workflow = AsyncMock()
    wf_store.update_timestamp = AsyncMock()
    return wf_store, wf


def _make_ar_store():
    """Build a mock AgentRunStore."""
    ar_store = MagicMock()
    run = MagicMock()
    run.id = 5
    ar_store.create_agent_run = AsyncMock(return_value=run)
    return ar_store


def _make_rp_store():
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


def _make_sm():
    """Build a real StateMachine."""
    from backend.orchestrator.state_machine import StateMachine

    return StateMachine()


@pytest.mark.asyncio
class TestWorkflowEngineLoop:
    """Test WorkflowEngine.run_workflow_loop behavior."""

    async def test_loop_transitions_through_all_states(self):
        """Verify run_workflow_loop transitions from NEW_STORE through DONE."""
        wf_store, wf = _make_wf_store(WorkflowState.NEW_STORE)
        ar_store = _make_ar_store()
        rp_store = _make_rp_store()
        emitter = _make_emitter()
        sm = _make_sm()

        state_transitions = []

        async def mock_run_single(store, workflow, state):
            state_transitions.append(state)
            next_state = sm.get_next_state(state)
            workflow.current_state = next_state.value
            return next_state

        # Create a mock engine that returns our mock _run_single_state
        mock_inner_engine = MagicMock()
        mock_inner_engine._run_single_state = mock_run_single

        mock_store = MagicMock()
        mock_store.id = 1
        mock_store.store_id = "test"

        mock_session = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        mock_store_store = MagicMock()
        mock_store_store.get_by_id = AsyncMock(return_value=mock_store)

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock()

        # Patch _build_loop_engine to return our mock engine
        with patch(
            "backend.orchestrator.engine.asyncio.sleep", new_callable=AsyncMock
        ) as mock_sleep, patch(
            "backend.orchestrator.engine.AsyncSessionLocal",
            return_value=mock_cm,
        ), patch(
            "backend.orchestrator.engine.StoreStore",
            return_value=mock_store_store,
        ), patch(
            "backend.orchestrator.engine.WorkflowStore",
            return_value=wf_store,
        ), patch(
            "backend.orchestrator.engine.AgentRunStore",
            return_value=ar_store,
        ), patch(
            "backend.orchestrator.engine.ReportStore",
            return_value=rp_store,
        ), patch(
            "backend.orchestrator.engine._build_loop_engine",
            return_value=mock_inner_engine,
        ):
            engine = WorkflowEngine(
                workflow_store=wf_store,
                agent_run_store=ar_store,
                report_store=rp_store,
                state_machine=sm,
                event_emitter=emitter,
                agent_runner=_make_runner_success(["analyzer"]),
            )
            await engine.run_workflow_loop(store_id=1, delay_seconds=0.01)

        # NEW_STORE -> DIAGNOSIS -> FOUNDATION -> DAILY_OPS -> WEEKLY_REPORT = 5 transitions
        # Done state exits without sleeping
        assert len(state_transitions) == 5
        assert mock_sleep.call_count == 4  # 4 sleeps between 5 states

    async def test_loop_stops_at_done(self):
        """Verify loop exits immediately when state is already DONE."""
        wf_store, wf = _make_wf_store(WorkflowState.DONE)
        ar_store = _make_ar_store()
        rp_store = _make_rp_store()
        emitter = _make_emitter()
        sm = _make_sm()

        engine = WorkflowEngine(
            workflow_store=wf_store,
            agent_run_store=ar_store,
            report_store=rp_store,
            state_machine=sm,
            event_emitter=emitter,
            agent_runner=_make_runner_success([]),
        )

        with patch("backend.orchestrator.engine.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await engine.run_workflow_loop(store_id=1, delay_seconds=0.01)

        # Should not have slept at all (already terminal)
        assert mock_sleep.call_count == 0

    async def test_loop_stops_at_manual_review(self):
        """Verify loop exits when MANUAL_REVIEW is reached."""
        wf_store, wf = _make_wf_store(WorkflowState.MANUAL_REVIEW)
        ar_store = _make_ar_store()
        rp_store = _make_rp_store()
        emitter = _make_emitter()
        sm = _make_sm()

        engine = WorkflowEngine(
            workflow_store=wf_store,
            agent_run_store=ar_store,
            report_store=rp_store,
            state_machine=sm,
            event_emitter=emitter,
            agent_runner=_make_runner_success([]),
        )

        with patch("backend.orchestrator.engine.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await engine.run_workflow_loop(store_id=1, delay_seconds=0.01)

        assert mock_sleep.call_count == 0

    async def test_loop_calls_run_single_state_per_iteration(self):
        """Verify _run_single_state is called once per state step."""
        wf_store, wf = _make_wf_store(WorkflowState.NEW_STORE)
        ar_store = _make_ar_store()
        rp_store = _make_rp_store()
        emitter = _make_emitter()
        sm = _make_sm()

        transition_count = 0

        async def mock_run_single(store, workflow, state):
            nonlocal transition_count
            transition_count += 1
            next_state = sm.get_next_state(state)
            workflow.current_state = next_state.value
            return next_state

        mock_inner_engine = MagicMock()
        mock_inner_engine._run_single_state = mock_run_single

        mock_store = MagicMock()
        mock_store.id = 1
        mock_store.store_id = "test"

        mock_session = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        mock_store_store = MagicMock()
        mock_store_store.get_by_id = AsyncMock(return_value=mock_store)

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock()

        with patch(
            "backend.orchestrator.engine.asyncio.sleep", new_callable=AsyncMock
        ), patch(
            "backend.orchestrator.engine.AsyncSessionLocal",
            return_value=mock_cm,
        ), patch(
            "backend.orchestrator.engine.StoreStore",
            return_value=mock_store_store,
        ), patch(
            "backend.orchestrator.engine.WorkflowStore",
            return_value=wf_store,
        ), patch(
            "backend.orchestrator.engine.AgentRunStore",
            return_value=ar_store,
        ), patch(
            "backend.orchestrator.engine.ReportStore",
            return_value=rp_store,
        ), patch(
            "backend.orchestrator.engine._build_loop_engine",
            return_value=mock_inner_engine,
        ):
            engine = WorkflowEngine(
                workflow_store=wf_store,
                agent_run_store=ar_store,
                report_store=rp_store,
                state_machine=sm,
                event_emitter=emitter,
                agent_runner=_make_runner_success(["analyzer"]),
            )
            await engine.run_workflow_loop(store_id=1, delay_seconds=0.01)

        # Should have run 5 state transitions (NEW_STORE through WEEKLY_REPORT)
        assert transition_count == 5

    async def test_loop_cancellation_clears_running_flag(self):
        """Verify CancelledError in _run_single_state clears is_running and returns."""
        wf_store, wf = _make_wf_store(WorkflowState.DIAGNOSIS)
        ar_store = _make_ar_store()
        rp_store = _make_rp_store()
        emitter = _make_emitter()
        sm = _make_sm()

        async def mock_run_single(store, workflow, state):
            raise asyncio.CancelledError()

        mock_inner_engine = MagicMock()
        mock_inner_engine._run_single_state = mock_run_single

        mock_store = MagicMock()
        mock_store.id = 1
        mock_store.store_id = "test"

        mock_session = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        mock_store_store = MagicMock()
        mock_store_store.get_by_id = AsyncMock(return_value=mock_store)

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock()

        with patch(
            "backend.orchestrator.engine.AsyncSessionLocal",
            return_value=mock_cm,
        ), patch(
            "backend.orchestrator.engine.StoreStore",
            return_value=mock_store_store,
        ), patch(
            "backend.orchestrator.engine.WorkflowStore",
            return_value=wf_store,
        ), patch(
            "backend.orchestrator.engine.AgentRunStore",
            return_value=ar_store,
        ), patch(
            "backend.orchestrator.engine.ReportStore",
            return_value=rp_store,
        ), patch(
            "backend.orchestrator.engine._build_loop_engine",
            return_value=mock_inner_engine,
        ):
            engine = WorkflowEngine(
                workflow_store=wf_store,
                agent_run_store=ar_store,
                report_store=rp_store,
                state_machine=sm,
                event_emitter=emitter,
                agent_runner=_make_runner_success([]),
            )

            result = await engine.run_workflow_loop(store_id=1, delay_seconds=0.01)

            # CancelledError is caught inside the loop; returns wf with is_running=False
            assert result is wf
            assert wf.is_running is False


@pytest.mark.asyncio
class TestWorkflowServiceLoop:
    """Test WorkflowService.start_workflow_loop and stop_workflow."""

    def _make_mock_service(self) -> WorkflowService:
        """Build a WorkflowService with mocked dependencies."""
        session = MagicMock()
        store_store = MagicMock()
        workflow_store = MagicMock()
        agent_run_store = MagicMock()
        event_log_store = MagicMock()
        report_store = MagicMock()
        state_machine = MagicMock()
        event_emitter = MagicMock()
        agent_runner = MagicMock()

        return WorkflowService(
            session,
            store_store,
            workflow_store,
            agent_run_store,
            event_log_store,
            report_store,
            state_machine,
            event_emitter,
            agent_runner,
        )

    async def test_start_workflow_loop_checks_done_terminal(self):
        """Workflow in DONE state should return 'already terminal'."""
        service = self._make_mock_service()
        service._require_store = AsyncMock(return_value=MagicMock(id=1, store_id="test"))

        mock_wf = MagicMock()
        mock_wf.current_state = WorkflowState.DONE.value
        service._workflow.get_by_store_id = AsyncMock(return_value=mock_wf)

        result = await service.start_workflow_loop(
            store_id=1,
            delay_seconds=3.0,
            task_registry={},
        )

        assert result["message"] == "Workflow already terminal"
        assert result["is_running"] is False

    async def test_start_workflow_loop_checks_manual_review_terminal(self):
        """Workflow in MANUAL_REVIEW should return 'already terminal'."""
        service = self._make_mock_service()
        service._require_store = AsyncMock(return_value=MagicMock(id=1, store_id="test"))

        mock_wf = MagicMock()
        mock_wf.current_state = WorkflowState.MANUAL_REVIEW.value
        service._workflow.get_by_store_id = AsyncMock(return_value=mock_wf)

        result = await service.start_workflow_loop(
            store_id=1,
            delay_seconds=3.0,
            task_registry={},
        )

        assert result["message"] == "Workflow already terminal"
        assert result["is_running"] is False

    async def test_stop_workflow_cancels_and_removes_task(self):
        """stop_workflow should cancel the task and remove it from registry."""
        service = self._make_mock_service()
        service._require_store = AsyncMock(return_value=MagicMock(id=1))

        mock_task = MagicMock()
        mock_task.done = MagicMock(return_value=False)
        registry = {1: mock_task}

        result = await service.stop_workflow(store_id=1, task_registry=registry)

        assert result["message"] == "Workflow stopped"
        assert result["is_running"] is False
        mock_task.cancel.assert_called_once()
        assert 1 not in registry

    async def test_stop_workflow_no_running_task(self):
        """stop_workflow with no running task returns 'No running workflow'."""
        service = self._make_mock_service()
        service._require_store = AsyncMock(return_value=MagicMock(id=1))

        result = await service.stop_workflow(store_id=1, task_registry={})

        assert result["message"] == "No running workflow"
        assert result["is_running"] is False

    async def test_concurrent_start_is_noop(self):
        """Starting a loop while one is running returns 'already running'."""
        service = self._make_mock_service()
        service._require_store = AsyncMock(return_value=MagicMock(id=1))

        mock_wf = MagicMock()
        mock_wf.current_state = WorkflowState.NEW_STORE.value
        service._workflow.get_by_store_id = AsyncMock(return_value=mock_wf)

        # Existing task that is not done
        mock_task = MagicMock()
        mock_task.done = MagicMock(return_value=False)
        registry = {1: mock_task}

        result = await service.start_workflow_loop(
            store_id=1,
            delay_seconds=3.0,
            force_restart=False,
            task_registry=registry,
        )

        assert result["message"] == "Workflow already running"
        assert result["is_running"] is True

    async def test_force_restart_cancels_existing_and_spawns_new(self):
        """force_restart=True cancels existing task before spawning new one."""
        service = self._make_mock_service()
        service._require_store = AsyncMock(return_value=MagicMock(id=1))

        mock_wf = MagicMock()
        mock_wf.current_state = WorkflowState.NEW_STORE.value
        service._workflow.get_by_store_id = AsyncMock(return_value=mock_wf)

        mock_task = MagicMock()
        mock_task.done = MagicMock(return_value=False)
        registry = {1: mock_task}

        new_mock_task = MagicMock()
        with patch(
            "backend.service.workflow.asyncio.get_running_loop"
        ) as mock_loop:
            mock_loop.return_value.create_task = MagicMock(return_value=new_mock_task)

            result = await service.start_workflow_loop(
                store_id=1,
                delay_seconds=3.0,
                force_restart=True,
                task_registry=registry,
            )

        mock_task.cancel.assert_called_once()
        # New task should be registered
        assert registry.get(1) is new_mock_task
        assert result["message"] == "Workflow started in background"
