from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import AsyncSessionLocal, get_db
from backend.models import (
    AgentRun,
    EventLog,
    Store,
    WorkflowInstance,
)
from backend.orchestrator.engine import WorkflowEngine
from backend.schemas import (
    AgentRunResponse,
    EventLogResponse,
    StoreResponse,
    TimelineResponse,
    WorkflowStatusResponse,
)

router = APIRouter()


@router.get("/{store_id}", response_model=StoreResponse)
async def get_store_detail(
    store_id: int,
    db: AsyncSession = Depends(get_db),
) -> StoreResponse:
    """Get store details."""
    store = await db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.post("/{store_id}/start")
async def start_workflow(
    store_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    """Start the workflow for a store."""
    store = await db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    async with AsyncSessionLocal() as session:
        eng = WorkflowEngine(session)
        try:
            await eng.run_workflow(store)
            await session.commit()
        except Exception as e:
            from backend.logging_config import get_logger

            logger = get_logger(__name__)
            logger.error(f"Workflow error for store {store_id}: {e}", exc_info=True)
            await session.rollback()
            raise

    return {"message": "Workflow started", "store_id": store_id}


@router.get("/{store_id}/status", response_model=WorkflowStatusResponse)
async def get_status(
    store_id: int,
    db: AsyncSession = Depends(get_db),
) -> WorkflowStatusResponse:
    """Query store current state and recent agent runs."""
    store = await db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    stmt = select(WorkflowInstance).where(WorkflowInstance.store_id == store_id)
    result = await db.execute(stmt)
    wf = result.scalar_one_or_none()

    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    recent_runs_stmt = (
        select(AgentRun)
        .where(AgentRun.store_id == store_id)
        .order_by(AgentRun.created_at.desc())
        .limit(10)
    )
    result = await db.execute(recent_runs_stmt)
    recent_runs = list(result.scalars().all())

    return WorkflowStatusResponse(
        store_id=store.id,
        store_name=store.name,
        current_state=wf.current_state,
        consecutive_failures=wf.consecutive_failures,
        retry_count=wf.retry_count,
        started_at=wf.started_at,
        recent_agent_runs=[
            AgentRunResponse(
                id=r.id,
                agent_type=r.agent_type,
                status=r.status,
                state_at_run=r.state_at_run,
                output_data=r.output_data or {},
                error_msg=r.error_msg,
                retry_count=r.retry_count,
                duration_ms=r.duration_ms,
                created_at=r.created_at,
            )
            for r in recent_runs
        ],
    )


@router.get("/{store_id}/timeline", response_model=TimelineResponse)
async def get_timeline(
    store_id: int,
    db: AsyncSession = Depends(get_db),
) -> TimelineResponse:
    """Query store event timeline."""
    store = await db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    stmt_wf = select(WorkflowInstance).where(WorkflowInstance.store_id == store_id)
    result = await db.execute(stmt_wf)
    wf = result.scalar_one_or_none()
    current_state = wf.current_state if wf else "NEW_STORE"

    events_stmt = (
        select(EventLog)
        .where(EventLog.store_id == store_id)
        .order_by(EventLog.created_at.desc())
        .limit(100)
    )
    result = await db.execute(events_stmt)
    events = list(result.scalars().all())

    return TimelineResponse(
        store_id=store.id,
        store_name=store.name,
        current_state=current_state,
        events=[
            EventLogResponse(
                id=e.id,
                event_type=e.event_type,
                from_state=e.from_state,
                to_state=e.to_state,
                agent_type=e.agent_type,
                message=e.message,
                extra_data=e.extra_data or {},
                created_at=e.created_at,
            )
            for e in events
        ],
    )


@router.post("/{store_id}/manual-takeover")
async def manual_takeover(
    store_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    """Trigger manual takeover for a store."""
    store = await db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    eng = WorkflowEngine(db)
    await eng.trigger_manual_takeover(store)
    await db.commit()

    return {"message": "Manual takeover triggered", "store_id": store_id}
