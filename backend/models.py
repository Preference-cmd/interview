import enum
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from backend.database import Base


class WorkflowState(str, enum.Enum):
    NEW_STORE = "NEW_STORE"
    DIAGNOSIS = "DIAGNOSIS"
    FOUNDATION = "FOUNDATION"
    DAILY_OPS = "DAILY_OPS"
    WEEKLY_REPORT = "WEEKLY_REPORT"
    DONE = "DONE"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class AgentStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


VALID_TRANSITIONS = {
    WorkflowState.NEW_STORE: {WorkflowState.DIAGNOSIS, WorkflowState.MANUAL_REVIEW},
    WorkflowState.DIAGNOSIS: {WorkflowState.FOUNDATION, WorkflowState.MANUAL_REVIEW},
    WorkflowState.FOUNDATION: {WorkflowState.DAILY_OPS, WorkflowState.MANUAL_REVIEW},
    WorkflowState.DAILY_OPS: {WorkflowState.WEEKLY_REPORT, WorkflowState.MANUAL_REVIEW},
    WorkflowState.WEEKLY_REPORT: {
        WorkflowState.DONE,
        WorkflowState.DAILY_OPS,
        WorkflowState.MANUAL_REVIEW,
    },
    WorkflowState.MANUAL_REVIEW: {
        WorkflowState.NEW_STORE,
        WorkflowState.DIAGNOSIS,
        WorkflowState.FOUNDATION,
        WorkflowState.DAILY_OPS,
    },
    WorkflowState.DONE: set(),
}


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
    ros_health = Column(String(16), default="unknown")  # low, medium, high
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
    started_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    store = relationship("Store", back_populates="workflow")


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("ix_agent_runs_store_created", "store_id", "created_at"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    agent_type = Column(
        String(64), nullable=False
    )  # analyzer, web_operator, mobile_operator, reporter
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


class EventLog(Base):
    __tablename__ = "event_logs"
    __table_args__ = (
        Index("ix_event_logs_store_created", "store_id", "created_at"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    event_type = Column(
        String(64), nullable=False, index=True
    )  # state_change, agent_start, agent_end, error, manual_takeover
    from_state = Column(String(32), nullable=True)
    to_state = Column(String(32), nullable=True)
    agent_type = Column(String(64), nullable=True)
    message = Column(Text)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.now(UTC), index=True)

    store = relationship("Store", back_populates="event_logs")


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_store_created", "store_id", "created_at"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    alert_type = Column(
        String(64), nullable=False
    )  # agent_failure, consecutive_failure, manual_required
    severity = Column(String(16), default="warning", index=True)  # info, warning, critical
    message = Column(Text)
    extra_data = Column(JSON, default=dict)
    acknowledged = Column(Integer, default=0, index=True)  # 0 = false, 1 = true
    created_at = Column(DateTime, default=datetime.now(UTC), index=True)

    store = relationship("Store", back_populates="alerts")


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index("ix_reports_store_created", "store_id", "created_at"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    report_type = Column(String(32), nullable=False, index=True)  # daily, weekly
    content_md = Column(Text, nullable=True)
    content_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.now(UTC), index=True)

    store = relationship("Store", back_populates="reports")
