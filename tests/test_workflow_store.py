import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.models._enums import WorkflowState
from backend.models import WorkflowInstance


def _make_session():
    sess = MagicMock()
    sess.execute = AsyncMock()
    sess.add = MagicMock()
    sess.flush = AsyncMock()
    return sess


@pytest.mark.asyncio
class TestCreateWorkflow:
    async def test_creates_workflow_instance(self):
        from backend.stores.workflow import WorkflowStore

        sess = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        sess.execute.return_value = mock_result

        store = WorkflowStore(sess)
        wf = await store.create_workflow(store_id=1)

        assert wf.store_id == 1
        assert wf.current_state == WorkflowState.NEW_STORE.value
        assert wf.consecutive_failures == 0
        sess.add.assert_called_once()
        sess.flush.assert_called_once()

    async def test_returns_existing_workflow(self):
        from backend.stores.workflow import WorkflowStore

        existing = WorkflowInstance(store_id=1, current_state=WorkflowState.DIAGNOSIS.value)
        sess = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=existing)
        sess.execute.return_value = mock_result

        store = WorkflowStore(sess)
        wf = await store.get_or_create_workflow(store_id=1)

        assert wf is existing
        sess.add.assert_not_called()


@pytest.mark.asyncio
class TestTransitionWorkflow:
    async def test_updates_state_and_flushes(self):
        from backend.stores.workflow import WorkflowStore

        sess = _make_session()
        wf = WorkflowInstance(store_id=1, current_state=WorkflowState.DIAGNOSIS.value)

        store = WorkflowStore(sess)
        await store.transition_workflow(wf, WorkflowState.DIAGNOSIS, WorkflowState.FOUNDATION)

        assert wf.current_state == WorkflowState.FOUNDATION.value
        sess.add.assert_called()
        sess.flush.assert_called()

    async def test_invalid_transition_returns_early(self):
        from backend.stores.workflow import WorkflowStore

        sess = _make_session()
        wf = WorkflowInstance(store_id=1, current_state=WorkflowState.DIAGNOSIS.value)

        store = WorkflowStore(sess)
        await store.transition_workflow(wf, WorkflowState.DIAGNOSIS, WorkflowState.DAILY_OPS)

        # State should not change for invalid transition
        assert wf.current_state == WorkflowState.DIAGNOSIS.value
        sess.add.assert_not_called()


@pytest.mark.asyncio
class TestTriggerManualTakeover:
    async def test_sets_manual_review_state(self):
        from backend.stores.workflow import WorkflowStore

        wf = WorkflowInstance(store_id=1, current_state=WorkflowState.DAILY_OPS.value, consecutive_failures=3)
        sess = _make_session()

        store = WorkflowStore(sess)
        result = await store.trigger_manual_takeover(wf)

        assert result.current_state == WorkflowState.MANUAL_REVIEW.value
        assert result.consecutive_failures == 0
