import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.models._enums import WorkflowState
from backend.orchestrator.state_machine import StateMachine


class TestGetAgentsForState:
    def setup_method(self):
        self.sm = StateMachine()

    def test_diagnosis_runs_analyzer(self):
        agents = self.sm.get_agents_for_state(WorkflowState.DIAGNOSIS)
        assert agents == ["analyzer"]

    def test_daily_ops_runs_web_and_mobile(self):
        agents = self.sm.get_agents_for_state(WorkflowState.DAILY_OPS)
        assert agents == ["web_operator", "mobile_operator"]

    def test_weekly_report_runs_reporter(self):
        agents = self.sm.get_agents_for_state(WorkflowState.WEEKLY_REPORT)
        assert agents == ["reporter"]

    def test_daily_ops_includes_web_operator(self):
        agents = self.sm.get_agents_for_state(WorkflowState.DAILY_OPS)
        assert "web_operator" in agents

    def test_daily_ops_includes_mobile_operator(self):
        agents = self.sm.get_agents_for_state(WorkflowState.DAILY_OPS)
        assert "mobile_operator" in agents

    def test_new_store_runs_no_agents(self):
        agents = self.sm.get_agents_for_state(WorkflowState.NEW_STORE)
        assert agents == []

    def test_manual_review_runs_no_agents(self):
        agents = self.sm.get_agents_for_state(WorkflowState.MANUAL_REVIEW)
        assert agents == []

    def test_done_runs_no_agents(self):
        agents = self.sm.get_agents_for_state(WorkflowState.DONE)
        assert agents == []


class TestGetNextState:
    def setup_method(self):
        self.sm = StateMachine()

    def test_new_store_to_diagnosis(self):
        assert self.sm.get_next_state(WorkflowState.NEW_STORE) == WorkflowState.DIAGNOSIS

    def test_diagnosis_to_foundation(self):
        assert self.sm.get_next_state(WorkflowState.DIAGNOSIS) == WorkflowState.FOUNDATION

    def test_foundation_to_daily_ops(self):
        assert self.sm.get_next_state(WorkflowState.FOUNDATION) == WorkflowState.DAILY_OPS

    def test_daily_ops_to_weekly_report(self):
        assert self.sm.get_next_state(WorkflowState.DAILY_OPS) == WorkflowState.WEEKLY_REPORT

    def test_weekly_report_to_done(self):
        assert self.sm.get_next_state(WorkflowState.WEEKLY_REPORT) == WorkflowState.DONE

    def test_done_stays_done(self):
        assert self.sm.get_next_state(WorkflowState.DONE) == WorkflowState.DONE

    def test_manual_review_stays_same(self):
        assert self.sm.get_next_state(WorkflowState.MANUAL_REVIEW) == WorkflowState.MANUAL_REVIEW


class TestIsValidTransition:
    def setup_method(self):
        self.sm = StateMachine()

    def test_new_store_to_diagnosis_valid(self):
        assert self.sm.is_valid_transition(WorkflowState.NEW_STORE, WorkflowState.DIAGNOSIS) is True

    def test_new_store_to_manual_review_valid(self):
        assert self.sm.is_valid_transition(WorkflowState.NEW_STORE, WorkflowState.MANUAL_REVIEW) is True

    def test_diagnosis_to_foundation_valid(self):
        assert self.sm.is_valid_transition(WorkflowState.DIAGNOSIS, WorkflowState.FOUNDATION) is True

    def test_diagnosis_to_daily_ops_invalid(self):
        assert self.sm.is_valid_transition(WorkflowState.DIAGNOSIS, WorkflowState.DAILY_OPS) is False

    def test_done_has_no_valid_transitions(self):
        for state in WorkflowState:
            assert self.sm.is_valid_transition(WorkflowState.DONE, state) is False


@pytest.mark.asyncio
class TestGetOrCreateWorkflow:
    async def test_creates_new_workflow(self):
        from backend.models import Store, WorkflowState

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute.return_value = mock_result

        store = MagicMock(spec=Store)
        store.id = 1
        store.store_id = "test_001"

        sm = StateMachine()
        wf = await sm.get_or_create_workflow(mock_db, store)

        assert wf.current_state == WorkflowState.NEW_STORE.value
        assert wf.consecutive_failures == 0
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    async def test_returns_existing_workflow(self):
        from backend.models import Store, WorkflowState, WorkflowInstance

        mock_db = AsyncMock()
        existing_wf = WorkflowInstance(
            store_id=1,
            current_state=WorkflowState.DIAGNOSIS.value,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=existing_wf)
        mock_db.execute.return_value = mock_result

        store = MagicMock(spec=Store)
        store.id = 1

        sm = StateMachine()
        wf = await sm.get_or_create_workflow(mock_db, store)

        assert wf is existing_wf
        mock_db.add.assert_not_called()


@pytest.mark.asyncio
class TestTriggerManualTakeover:
    async def test_sets_manual_review_state(self):
        from backend.models import Store, WorkflowState, WorkflowInstance

        existing_wf = WorkflowInstance(
            store_id=1,
            current_state=WorkflowState.DAILY_OPS.value,
            consecutive_failures=2,
        )
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=existing_wf)
        mock_db.execute.return_value = mock_result

        store = MagicMock(spec=Store)
        store.id = 1
        store.store_id = "test_001"

        sm = StateMachine()
        wf = await sm.trigger_manual_takeover(mock_db, store)

        assert wf.current_state == WorkflowState.MANUAL_REVIEW.value
        assert wf.consecutive_failures == 0
        mock_db.add.assert_called()
        mock_db.flush.assert_called()
