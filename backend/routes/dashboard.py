from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import AgentRun, Alert, Store, WorkflowInstance, WorkflowState
from backend.schemas import DashboardSummaryResponse

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
) -> DashboardSummaryResponse:
    """Global overview: state distribution, anomalies, queue backlog."""
    # Total stores
    result = await db.execute(select(func.count(Store.id)))
    total = result.scalar() or 0

    # State distribution
    state_dist: dict[str, int] = {}
    result = await db.execute(select(WorkflowInstance))
    wfs = result.scalars().all()
    for wf in wfs:
        state_dist[wf.current_state] = state_dist.get(wf.current_state, 0) + 1

    # Anomaly count (non-acknowledged alerts)
    result = await db.execute(
        select(func.count(Alert.id)).where(Alert.acknowledged == 0),
    )
    anomaly_count = result.scalar() or 0

    # Manual review queue
    result = await db.execute(
        select(WorkflowInstance, Store)
        .join(Store, WorkflowInstance.store_id == Store.id)
        .where(WorkflowInstance.current_state == WorkflowState.MANUAL_REVIEW.value),
    )
    rows = result.all()
    manual_review_queue = [
        {"store_id": wf.store_id, "store_name": s.name, "state": wf.current_state} for wf, s in rows
    ]

    # Recent alerts
    result = await db.execute(
        select(Alert, Store)
        .join(Store, Alert.store_id == Store.id)
        .order_by(Alert.created_at.desc())
        .limit(20),
    )
    alert_rows = result.all()
    recent_alerts = [
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
        for a, s in alert_rows
    ]

    # Recent agent runs
    result = await db.execute(
        select(AgentRun, Store)
        .join(Store, AgentRun.store_id == Store.id)
        .order_by(AgentRun.created_at.desc())
        .limit(20),
    )
    run_rows = result.all()
    recent_runs = [
        {
            "id": r.id,
            "store_id": r.store_id,
            "store_name": s.name,
            "agent_type": r.agent_type,
            "status": r.status,
            "duration_ms": r.duration_ms,
            "created_at": r.created_at.isoformat(),
        }
        for r, s in run_rows
    ]

    return DashboardSummaryResponse(
        total_stores=total,
        state_distribution=state_dist,
        anomaly_count=anomaly_count,
        manual_review_queue=manual_review_queue,
        recent_alerts=recent_alerts,
        recent_agent_runs=recent_runs,
    )
