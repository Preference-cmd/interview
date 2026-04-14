from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class StoreImportItem(BaseModel):
    store_id: str
    name: str
    city: str | None = None
    category: str | None = None
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
    city: str | None = None
    category: str | None = None
    rating: float = 0.0
    monthly_orders: int = 0
    gmv_last_7d: float = 0.0
    review_count: int = 0
    review_reply_rate: float = 0.0
    ros_health: str = "unknown"
    competitor_avg_discount: float = 0.0
    issues: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
