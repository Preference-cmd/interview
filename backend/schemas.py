from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


# --- Store schemas ---

class StoreImportItem(BaseModel):
    store_id: str
    name: str
    city: Optional[str] = None
    category: Optional[str] = None
    rating: float = 0.0
    monthly_orders: int = 0
    gmv_last_7d: float = 0.0
    review_count: int = 0
    review_reply_rate: float = 0.0
    ros_health: str = "unknown"
    competitor_avg_discount: float = 0.0
    issues: list[str] = Field(default_factory=list)
    raw_data: dict = Field(default_factory=dict)


class StoreImportRequest(BaseModel):
    stores: list[StoreImportItem]


class StoreResponse(BaseModel):
    id: int
    store_id: str
    name: str
    city: Optional[str]
    category: Optional[str]
    rating: float
    monthly_orders: int
    gmv_last_7d: float
    review_count: int
    review_reply_rate: float
    ros_health: str
    competitor_avg_discount: float
    issues: list[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Workflow schemas ---

class WorkflowStatusResponse(BaseModel):
    store_id: int
    store_name: str
    current_state: str
    consecutive_failures: int
    retry_count: int
    started_at: Optional[datetime]
    recent_agent_runs: list["AgentRunResponse"]


# --- Agent schemas ---

class AgentRunResponse(BaseModel):
    id: int
    agent_type: str
    status: str
    state_at_run: Optional[str]
    output_data: dict
    error_msg: Optional[str]
    retry_count: int
    duration_ms: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Event timeline ---

class EventLogResponse(BaseModel):
    id: int
    event_type: str
    from_state: Optional[str]
    to_state: Optional[str]
    agent_type: Optional[str]
    message: Optional[str]
    extra_data: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TimelineResponse(BaseModel):
    store_id: int
    store_name: str
    current_state: str
    events: list[EventLogResponse]


# --- Dashboard ---

class DashboardSummaryResponse(BaseModel):
    total_stores: int
    state_distribution: dict[str, int]
    anomaly_count: int
    manual_review_queue: list[dict]
    recent_alerts: list[dict]
    recent_agent_runs: list[dict]


# --- Alert schemas ---

class AlertResponse(BaseModel):
    id: int
    store_id: int
    alert_type: str
    severity: str
    message: Optional[str]
    acknowledged: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Update forward refs
AgentRunResponse.model_rebuild()
