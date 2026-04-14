from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base
from backend.models._enums import AgentStatus


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("ix_agent_runs_store_created", "store_id", "created_at"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    agent_type = Column(String(64), nullable=False)
    status = Column(String(16), default=AgentStatus.PENDING.value, index=True)
    state_at_run = Column(String(32), nullable=True)
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    error_msg = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now(UTC), index=True)
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    store = relationship("Store", back_populates="agent_runs")
