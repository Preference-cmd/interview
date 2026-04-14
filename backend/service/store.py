from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas import StoreImportRequest, StoreResponse
from backend.stores.store import StoreStore


class StoreService:
    def __init__(self, session: AsyncSession, store_store: StoreStore) -> None:
        self._session = session
        self._store = store_store

    async def import_stores(
        self, request: StoreImportRequest
    ) -> list[StoreResponse]:
        stores = await self._store.import_or_update(request.stores)
        await self._session.commit()
        for store in stores:
            await self._session.refresh(store)
        return [StoreResponse.model_validate(s) for s in stores]

    async def list_stores(self) -> list[StoreResponse]:
        stores = await self._store.list_all()
        return [StoreResponse.model_validate(s) for s in stores]
