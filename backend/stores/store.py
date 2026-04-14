from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Store
from backend.schemas import StoreImportItem


class StoreStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, store_id: int) -> Store | None:
        return await self._session.get(Store, store_id)

    async def import_or_update(self, items: list[StoreImportItem]) -> list[Store]:
        imported: list[Store] = []
        for item in items:
            store = await self.get_by_store_id(item.store_id)
            if store:
                for field, value in item.model_dump().items():
                    if field != "store_id":
                        setattr(store, field, value)
                store.updated_at = datetime.now(UTC)
                imported.append(store)
            else:
                store = Store(**item.model_dump())
                self._session.add(store)
                imported.append(store)
        await self._session.flush()
        return imported

    async def get_by_store_id(self, store_id: str) -> Store | None:
        stmt = select(Store).where(Store.store_id == store_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Store]:
        stmt = select(Store).order_by(Store.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
