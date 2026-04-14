from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AgentRunResponse(BaseModel):
    id: int
    agent_type: str
    status: str
    state_at_run: str | None = None
    output_data: dict = {}
    error_msg: str | None = None
    retry_count: int = 0
    duration_ms: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}
