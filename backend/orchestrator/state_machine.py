from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.logging_config import get_logger
from backend.models import (
    VALID_TRANSITIONS,
    Store,
    WorkflowInstance,
    WorkflowState,
)

logger = get_logger(__name__)


class StateMachine:
    """
    Manages workflow state transitions and agent-to-state mappings.
    """

    STATES_REQUIRING_ANALYZER = {WorkflowState.DIAGNOSIS}
    STATES_REQUIRING_WEB_OPS = {WorkflowState.FOUNDATION, WorkflowState.DAILY_OPS}
    STATES_REQUIRING_MOBILE_OPS = {WorkflowState.DAILY_OPS}
    STATES_REQUIRING_REPORTER = {WorkflowState.WEEKLY_REPORT}

    def get_agents_for_state(self, state: WorkflowState) -> list[str]:
        agents: list[str] = []
        if state in self.STATES_REQUIRING_ANALYZER:
            agents.append("analyzer")
        if state in self.STATES_REQUIRING_WEB_OPS:
            agents.append("web_operator")
        if state in self.STATES_REQUIRING_MOBILE_OPS:
            agents.append("mobile_operator")
        if state in self.STATES_REQUIRING_REPORTER:
            agents.append("reporter")
        return agents

    def get_next_state(self, current: WorkflowState) -> WorkflowState:
        next_map: dict[WorkflowState, WorkflowState] = {
            WorkflowState.NEW_STORE: WorkflowState.DIAGNOSIS,
            WorkflowState.DIAGNOSIS: WorkflowState.FOUNDATION,
            WorkflowState.FOUNDATION: WorkflowState.DAILY_OPS,
            WorkflowState.DAILY_OPS: WorkflowState.WEEKLY_REPORT,
            WorkflowState.WEEKLY_REPORT: WorkflowState.DONE,
        }
        return next_map.get(current, current)

    def is_valid_transition(self, from_: WorkflowState, to: WorkflowState) -> bool:
        return to in VALID_TRANSITIONS.get(from_, set())
