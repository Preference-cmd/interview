from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Store
from backend.schemas import DashboardSummaryResponse
from backend.stores.agent_run import AgentRunStore
from backend.stores.alert import AlertStore
from backend.stores.store import StoreStore
from backend.stores.workflow import WorkflowStore


class DashboardService:
    def __init__(
        self,
        session: AsyncSession,
        store_store: StoreStore,
        alert_store: AlertStore,
        agent_run_store: AgentRunStore,
        workflow_store: WorkflowStore,
    ) -> None:
        self._session = session
        self._store = store_store
        self._alert = alert_store
        self._agent_run = agent_run_store
        self._workflow = workflow_store

    async def get_summary(self) -> DashboardSummaryResponse:
        # Total stores
        result = await self._session.execute(select(func.count(Store.id)))
        total = result.scalar() or 0

        # State distribution
        state_dist = await self._workflow.get_state_distribution()

        # Anomaly count
        anomaly_count = await self._alert.count_unacknowledged()

        # Manual review queue
        queue_rows = await self._workflow.get_manual_review_queue()
        manual_review_queue = [
            {
                "store_id": wf.store_id,
                "store_name": s.name,
                "state": wf.current_state,
            }
            for wf, s in queue_rows
        ]

        # Recent alerts
        alert_rows = await self._alert.list_recent(limit=20)
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
        run_rows = await self._agent_run.list_recent(limit=20)
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
