from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Alert, EventLog


class EventEmitter:
    """
    Handles event logging and alert creation.
    """

    async def log_event(
        self,
        db: AsyncSession,
        store_id: int,
        event_type: str,
        from_state: str | None = None,
        to_state: str | None = None,
        agent_type: str | None = None,
        message: str | None = None,
        extra_data: dict | None = None,
    ) -> None:
        """Create a structured event log entry."""
        event = EventLog(
            store_id=store_id,
            event_type=event_type,
            from_state=from_state,
            to_state=to_state,
            agent_type=agent_type,
            message=message,
            extra_data=extra_data or {},
        )
        db.add(event)

    async def create_alert(
        self,
        db: AsyncSession,
        store_id: int,
        alert_type: str,
        severity: str,
        message: str,
        extra_data: dict | None = None,
    ) -> None:
        """Create an alert for anomalies."""
        alert = Alert(
            store_id=store_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            extra_data=extra_data or {},
        )
        db.add(alert)
