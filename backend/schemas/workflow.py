from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from backend.schemas.agent import AgentRunResponse


class WorkflowStartRequest(BaseModel):
    delay_seconds: float = 3.0
    force_restart: bool = False


class WorkflowStatusResponse(BaseModel):
    store_id: int
    store_name: str
    current_state: str
    consecutive_failures: int = 0
    retry_count: int = 0
    is_running: bool = False
    started_at: datetime | None = None
    recent_agent_runs: list[AgentRunResponse] = []


class DashboardSummaryResponse(BaseModel):
    total_stores: int
    state_distribution: dict[str, int]
    anomaly_count: int
    manual_review_queue: list[dict]
    recent_alerts: list[dict]
    recent_agent_runs: list[dict]
