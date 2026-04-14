from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Alert, Store

router = APIRouter()


@router.get("")
async def list_alerts(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """List all alerts."""
    result = await db.execute(
        select(Alert, Store)
        .join(Store, Alert.store_id == Store.id)
        .order_by(Alert.created_at.desc())
        .limit(100),
    )
    rows = result.all()
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


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    """Acknowledge an alert."""
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = 1
    await db.flush()
    await db.commit()
    return {"message": "Alert acknowledged", "alert_id": alert_id}
