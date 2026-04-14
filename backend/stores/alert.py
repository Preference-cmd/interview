from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Alert, Store


class AlertStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_recent(self, limit: int = 20) -> list[tuple[Alert, Store]]:
        stmt = (
            select(Alert, Store)
            .join(Store, Alert.store_id == Store.id)
            .order_by(Alert.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.all())

    async def count_unacknowledged(self) -> int:
        stmt = select(func.count(Alert.id)).where(Alert.acknowledged == 0)
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def acknowledge(self, alert_id: int) -> bool:
        alert = await self._session.get(Alert, alert_id)
        if not alert:
            return False
        alert.acknowledged = 1
        await self._session.flush()
        return True
