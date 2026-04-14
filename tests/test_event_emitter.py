import pytest
from unittest.mock import AsyncMock

from backend.orchestrator.event_emitter import EventEmitter


@pytest.mark.asyncio
class TestLogEvent:
    async def test_creates_eventlog_with_all_fields(self):
        mock_db = AsyncMock()

        emitter = EventEmitter()
        await emitter.log_event(
            db=mock_db,
            store_id=1,
            event_type="agent_run",
            from_state="DIAGNOSIS",
            to_state="DIAGNOSIS",
            agent_type="analyzer",
            message="analyzer success (150ms)",
            extra_data={"run_id": 5, "error": None},
        )

        mock_db.add.assert_called_once()
        added_event = mock_db.add.call_args[0][0]
        assert added_event.store_id == 1
        assert added_event.event_type == "agent_run"
        assert added_event.from_state == "DIAGNOSIS"
        assert added_event.to_state == "DIAGNOSIS"
        assert added_event.agent_type == "analyzer"
        assert added_event.message == "analyzer success (150ms)"
        assert added_event.extra_data == {"run_id": 5, "error": None}

    async def test_creates_eventlog_with_minimal_fields(self):
        mock_db = AsyncMock()

        emitter = EventEmitter()
        await emitter.log_event(
            db=mock_db,
            store_id=2,
            event_type="workflow_created",
        )

        mock_db.add.assert_called_once()
        added_event = mock_db.add.call_args[0][0]
        assert added_event.store_id == 2
        assert added_event.event_type == "workflow_created"
        assert added_event.from_state is None
        assert added_event.agent_type is None

    async def test_defaults_extra_data_to_empty_dict(self):
        mock_db = AsyncMock()

        emitter = EventEmitter()
        await emitter.log_event(
            db=mock_db,
            store_id=3,
            event_type="state_change",
        )

        added_event = mock_db.add.call_args[0][0]
        assert added_event.extra_data == {}


@pytest.mark.asyncio
class TestCreateAlert:
    async def test_creates_alert_with_all_fields(self):
        mock_db = AsyncMock()

        emitter = EventEmitter()
        await emitter.create_alert(
            db=mock_db,
            store_id=1,
            alert_type="consecutive_failure",
            severity="critical",
            message="连续3次失败，触发人工接管",
            extra_data={"failures": 3},
        )

        mock_db.add.assert_called_once()
        added_alert = mock_db.add.call_args[0][0]
        assert added_alert.store_id == 1
        assert added_alert.alert_type == "consecutive_failure"
        assert added_alert.severity == "critical"
        assert added_alert.message == "连续3次失败，触发人工接管"
        assert added_alert.extra_data == {"failures": 3}

    async def test_defaults_extra_data_to_empty_dict(self):
        mock_db = AsyncMock()

        emitter = EventEmitter()
        await emitter.create_alert(
            db=mock_db,
            store_id=2,
            alert_type="manual_takeover",
            severity="warning",
            message="人工接管已触发",
        )

        added_alert = mock_db.add.call_args[0][0]
        assert added_alert.extra_data == {}
