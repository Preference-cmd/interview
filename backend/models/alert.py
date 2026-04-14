from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_store_created", "store_id", "created_at"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    alert_type = Column(String(64), nullable=False)
    severity = Column(String(16), default="warning", index=True)
    message = Column(Text)
    extra_data = Column(JSON, default=dict)
    acknowledged = Column(Integer, default=0, index=True)
    created_at = Column(DateTime, default=datetime.now(UTC), index=True)

    store = relationship("Store", back_populates="alerts")
