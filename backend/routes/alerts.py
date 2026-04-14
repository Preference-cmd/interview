from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.service import AlertService
from backend.stores import AlertStore

router = APIRouter()


@router.get("")
async def list_alerts(db: AsyncSession = Depends(get_db)) -> list[dict]:
    service = AlertService(db, AlertStore(db))
    return await service.list_alerts()


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    service = AlertService(db, AlertStore(db))
    return await service.acknowledge(alert_id)
