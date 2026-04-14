from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Store
from backend.schemas import (
    StoreImportRequest,
    StoreResponse,
)

router = APIRouter()


@router.post("/import", response_model=list[StoreResponse])
async def import_stores(
    request: StoreImportRequest,
    db: AsyncSession = Depends(get_db),
) -> list[StoreResponse]:
    """Batch import store data."""
    imported = []
    for item in request.stores:
        stmt = select(Store).where(Store.store_id == item.store_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            for field, value in item.model_dump().items():
                if field != "store_id":
                    setattr(existing, field, value)
            from datetime import UTC, datetime

            existing.updated_at = datetime.now(UTC)
            imported.append(existing)
        else:
            store = Store(**item.model_dump())
            db.add(store)
            imported.append(store)
    await db.flush()
    await db.commit()
    for store in imported:
        await db.refresh(store)
    return imported


@router.get("", response_model=list[StoreResponse])
async def list_stores(db: AsyncSession = Depends(get_db)) -> list[StoreResponse]:
    """List all stores."""
    stmt = select(Store).order_by(Store.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())
