from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.stores.alert import AlertStore


class AlertService:
    def __init__(self, session: AsyncSession, alert_store: AlertStore) -> None:
        self._session = session
        self._alert = alert_store

    async def list_alerts(self) -> list[dict]:
        rows = await self._alert.list_recent(limit=100)
        return [
            {
                "id": a.id,
                "store_id": a.store_id,
                "store_name": s.name,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "message": a.message,
                "acknowledged": bool(a.acknowledged),
                "created_at": a.created_at.isoformat(),
            }
            for a, s in rows
        ]

    async def acknowledge(self, alert_id: int) -> dict[str, int | str]:
        found = await self._alert.acknowledge(alert_id)
        if not found:
            raise HTTPException(status_code=404, detail="Alert not found")
        await self._session.commit()
        return {"message": "Alert acknowledged", "alert_id": alert_id}
