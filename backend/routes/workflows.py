from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.analyzer import AnalyzerAgent
from backend.agents.mobile_operator import MobileOperatorAgent
from backend.agents.reporter import ReporterAgent
from backend.agents.web_operator import WebOperatorAgent
from backend.database import get_db
from backend.orchestrator import AgentRunner, EventEmitter, StateMachine
from backend.schemas import (
    StoreResponse,
    TimelineResponse,
    WorkflowStatusResponse,
)
from backend.service import WorkflowService
from backend.stores import AgentRunStore, EventLogStore, StoreStore, WorkflowStore

router = APIRouter()


def _build_workflow_service(
    db: AsyncSession,
    store_store: StoreStore,
    workflow_store: WorkflowStore,
    agent_run_store: AgentRunStore,
    event_log_store: EventLogStore,
) -> WorkflowService:
    agents = {
        "analyzer": AnalyzerAgent(),
        "web_operator": WebOperatorAgent(failure_rate=0.2),
        "mobile_operator": MobileOperatorAgent(failure_rate=0.25),
        "reporter": ReporterAgent(),
    }
    return WorkflowService(
        db,
        store_store,
        workflow_store,
        agent_run_store,
        event_log_store,
        StateMachine(),
        EventEmitter(),
        AgentRunner(agents),
    )


@router.get("/{store_id}", response_model=StoreResponse)
async def get_store_detail(
    store_id: int,
    db: AsyncSession = Depends(get_db),
) -> StoreResponse:
    service = _build_workflow_service(
        db,
        StoreStore(db),
        WorkflowStore(db),
        AgentRunStore(db),
        EventLogStore(db),
    )
    return await service.get_store_detail(store_id)


@router.post("/{store_id}/start")
async def start_workflow(
    store_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    service = _build_workflow_service(
        db,
        StoreStore(db),
        WorkflowStore(db),
        AgentRunStore(db),
        EventLogStore(db),
    )
    return await service.start_workflow(store_id)


@router.get("/{store_id}/status", response_model=WorkflowStatusResponse)
async def get_status(
    store_id: int,
    db: AsyncSession = Depends(get_db),
) -> WorkflowStatusResponse:
    service = _build_workflow_service(
        db,
        StoreStore(db),
        WorkflowStore(db),
        AgentRunStore(db),
        EventLogStore(db),
    )
    return await service.get_status(store_id)


@router.get("/{store_id}/timeline", response_model=TimelineResponse)
async def get_timeline(
    store_id: int,
    db: AsyncSession = Depends(get_db),
) -> TimelineResponse:
    service = _build_workflow_service(
        db,
        StoreStore(db),
        WorkflowStore(db),
        AgentRunStore(db),
        EventLogStore(db),
    )
    return await service.get_timeline(store_id)


@router.post("/{store_id}/manual-takeover")
async def manual_takeover(
    store_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    service = _build_workflow_service(
        db,
        StoreStore(db),
        WorkflowStore(db),
        AgentRunStore(db),
        EventLogStore(db),
    )
    return await service.manual_takeover(store_id)
