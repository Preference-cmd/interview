from __future__ import annotations

import enum


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


VALID_TRANSITIONS: dict[str, set[str]] = {
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
