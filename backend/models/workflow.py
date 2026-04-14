from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.database import Base
from backend.models._enums import WorkflowState


class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"
    __table_args__ = (
        UniqueConstraint("store_id", name="uq_workflow_store_id"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    current_state = Column(String(32), default=WorkflowState.NEW_STORE.value, index=True)
    consecutive_failures = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    is_running = Column(Boolean, default=False, index=True)
    started_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    store = relationship("Store", back_populates="workflow")
