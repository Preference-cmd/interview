from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class EventLog(Base):
    __tablename__ = "event_logs"
    __table_args__ = (
        Index("ix_event_logs_store_created", "store_id", "created_at"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    from_state = Column(String(32), nullable=True)
    to_state = Column(String(32), nullable=True)
    agent_type = Column(String(64), nullable=True)
    message = Column(Text)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.now(UTC), index=True)

    store = relationship("Store", back_populates="event_logs")
