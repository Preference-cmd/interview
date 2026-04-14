from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas import DashboardSummaryResponse
from backend.service import DashboardService
from backend.stores import AgentRunStore, AlertStore, StoreStore, WorkflowStore

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
) -> DashboardSummaryResponse:
    service = DashboardService(
        db,
        StoreStore(db),
        AlertStore(db),
        AgentRunStore(db),
        WorkflowStore(db),
    )
    return await service.get_summary()
