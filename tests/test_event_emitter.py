from unittest.mock import MagicMock

from backend.models import Alert, EventLog
from backend.orchestrator.event_emitter import EventEmitter


class TestEmitEvent:
    def test_adds_event_to_session(self):
        mock_db = MagicMock()

        emitter = EventEmitter(mock_db)
        event = EventLog(
            store_id=1,
            event_type="agent_run",
            from_state="DIAGNOSIS",
            to_state="DIAGNOSIS",
            agent_type="analyzer",
            message="analyzer success (150ms)",
            extra_data={"run_id": 5, "error": None},
        )

        emitter.emit_event(event)

        mock_db.add.assert_called_once_with(event)

    def test_adds_minimal_event(self):
        mock_db = MagicMock()

        emitter = EventEmitter(mock_db)
        event = EventLog(store_id=2, event_type="workflow_created")

        emitter.emit_event(event)

        mock_db.add.assert_called_once_with(event)


class TestEmitAlert:
    def test_adds_alert_to_session(self):
        mock_db = MagicMock()

        emitter = EventEmitter(mock_db)
        alert = Alert(
            store_id=1,
            alert_type="consecutive_failure",
            severity="critical",
            message="连续3次失败",
            extra_data={"failures": 3},
        )

        emitter.emit_alert(alert)

        mock_db.add.assert_called_once_with(alert)

    def test_adds_warning_alert(self):
        mock_db = MagicMock()

        emitter = EventEmitter(mock_db)
        alert = Alert(
            store_id=2,
            alert_type="manual_takeover",
            severity="warning",
            message="人工接管已触发",
        )

        emitter.emit_alert(alert)

        mock_db.add.assert_called_once_with(alert)
