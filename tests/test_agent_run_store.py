import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.models import AgentRun


def _make_session():
    sess = MagicMock()
    sess.add = MagicMock()
    sess.flush = AsyncMock()
    return sess


@pytest.mark.asyncio
class TestCreateAgentRun:
    async def test_creates_agent_run_with_all_fields(self):
        from backend.stores.agent_run import AgentRunStore

        sess = _make_session()
        store = AgentRunStore(sess)

        await store.create_agent_run(
            store_id=1,
            agent_type="analyzer",
            status="success",
            state_at_run="DIAGNOSIS",
            input_data={"store_data": {}},
            output_data={"result": "ok"},
            error_msg=None,
            retry_count=0,
            duration_ms=150,
        )

        sess.add.assert_called_once()
        sess.flush.assert_called_once()
        added = sess.add.call_args[0][0]
        assert isinstance(added, AgentRun)
        assert added.store_id == 1
        assert added.agent_type == "analyzer"
        assert added.status == "success"
        assert added.state_at_run == "DIAGNOSIS"
        assert added.retry_count == 0
        assert added.duration_ms == 150
