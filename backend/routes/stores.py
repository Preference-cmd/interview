from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas import StoreImportRequest, StoreResponse
from backend.service import StoreService
from backend.stores import StoreStore

router = APIRouter()


@router.post("/import", response_model=list[StoreResponse])
async def import_stores(
    request: StoreImportRequest,
    db: AsyncSession = Depends(get_db),
) -> list[StoreResponse]:
    service = StoreService(db, StoreStore(db))
    return await service.import_stores(request)


@router.get("", response_model=list[StoreResponse])
async def list_stores(db: AsyncSession = Depends(get_db)) -> list[StoreResponse]:
    service = StoreService(db, StoreStore(db))
    return await service.list_stores()
