from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String
from sqlalchemy.orm import relationship

from backend.database import Base


class Store(Base):
    __tablename__ = "stores"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(256), nullable=False)
    city = Column(String(64))
    category = Column(String(64))
    rating = Column(Float, default=0.0)
    monthly_orders = Column(Integer, default=0)
    gmv_last_7d = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    review_reply_rate = Column(Float, default=0.0)
    ros_health = Column(String(16), default="unknown")
    competitor_avg_discount = Column(Float, default=0.0)
    issues = Column(JSON, default=list)
    raw_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    workflow = relationship("WorkflowInstance", back_populates="store", uselist=False)
    agent_runs = relationship("AgentRun", back_populates="store")
    event_logs = relationship("EventLog", back_populates="store")
    alerts = relationship("Alert", back_populates="store")
    reports = relationship("Report", back_populates="store")
