from __future__ import annotations

from backend.models import Alert, EventLog


class EventEmitter:
    """
    Thin wrapper that persists EventLog and Alert model instances.
    """

    def __init__(self, db) -> None:
        self._db = db

    def emit_event(self, event: EventLog) -> None:
        """Persist an event log entry."""
        self._db.add(event)

    def emit_alert(self, alert: Alert) -> None:
        """Persist an alert entry."""
        self._db.add(alert)
