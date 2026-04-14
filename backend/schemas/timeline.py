from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EventLogResponse(BaseModel):
    id: int
    event_type: str
    from_state: str | None = None
    to_state: str | None = None
    agent_type: str | None = None
    message: str | None = None
    extra_data: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TimelineResponse(BaseModel):
    store_id: int
    store_name: str
    current_state: str
    events: list[EventLogResponse]
