# Routes Modularization + Engine Async Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `main.py`'s 12 routes into dedicated `routes/` modules, convert all routes and `WorkflowEngine` to use async SQLAlchemy session, and fix P1 issues (`retry_count` tracking, redundant `failure_rate`).

**Architecture:** Each route domain gets its own `APIRouter`. All `db.execute()` → `await session.execute()`. `WorkflowEngine` becomes fully async with `AsyncSession`.

**Tech Stack:** FastAPI, SQLAlchemy 2.x async, aiosqlite

---

## File Map

```
backend/
├── main.py                ← stripped to app + router registration + lifespan
├── routes/
│   ├── __init__.py        ← re-exports all routers
│   ├── stores.py          ← /stores/import, /stores (GET list)
│   ├── workflows.py       ← /stores/{id}/start, /stores/{id}/status,
│   │                         /stores/{id}/timeline, /stores/{id}/manual-takeover
│   │                         /stores/{id} (GET detail)
│   ├── dashboard.py       ← /dashboard/summary
│   └── alerts.py          ← /alerts, /alerts/{id}/acknowledge
├── orchestrator/
│   └── engine.py          ← AsyncSession throughout, all methods async
├── agents/
│   └── base.py            ← AgentStatus removed (done in Plan 2)
└── logging_config.py
```

---

## Task 1: Create `routes/stores.py`

**Files:**
- Create: `backend/routes/__init__.py`
- Create: `backend/routes/stores.py`
- Read: `backend/main.py` lines 61-89 (import_stores, list_stores)

- [ ] **Step 1: Write `backend/routes/stores.py`**

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Store
from backend.schemas import (
    StoreImportItem,
    StoreImportRequest,
    StoreResponse,
)

router = APIRouter()


@router.post("/import", response_model=list[StoreResponse])
async def import_stores(
    request: StoreImportRequest,
    db: AsyncSession = Depends(get_db),
) -> list[StoreResponse]:
    """Batch import store data."""
    imported = []
    for item in request.stores:
        stmt = select(Store).where(Store.store_id == item.store_id)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            for field, value in item.model_dump().items():
                if field != "store_id":
                    setattr(existing, field, value)
            from datetime import UTC, datetime
            existing.updated_at = datetime.now(UTC)
            imported.append(existing)
        else:
            store = Store(**item.model_dump())
            db.add(store)
            imported.append(store)
    await db.flush()
    await db.commit()
    # Refresh to load relationships
    for store in imported:
        await db.refresh(store)
    return imported


@router.get("", response_model=list[StoreResponse])
async def list_stores(db: AsyncSession = Depends(get_db)) -> list[StoreResponse]:
    """List all stores."""
    stmt = select(Store).order_by(Store.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())
```

- [ ] **Step 2: Write `backend/routes/__init__.py`**

```python
from __future__ import annotations

from .alerts import router as alerts_router
from .dashboard import router as dashboard_router
from .stores import router as stores_router
from .workflows import router as workflows_router

__all__ = [
    "alerts_router",
    "dashboard_router",
    "stores_router",
    "workflows_router",
]
```

- [ ] **Step 3: Run lint**

Run: `cd backend && uv run ruff check routes/`
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add backend/routes/stores.py backend/routes/__init__.py
git commit -m "feat(routes): split stores routes into routes/stores.py

- POST /stores/import, GET /stores
- All async with AsyncSession"
```

---

## Task 2: Create `routes/workflows.py`

**Files:**
- Create: `backend/routes/workflows.py`
- Read: `backend/main.py` lines 91-216 (all /stores/{id}/* routes)

This is the largest route file. Key changes:
- All `db.execute()` → `await db.execute()`
- All `db.get(Model, id)` → `await db.get(Model, id)` (SQLAlchemy 2.x supports await on `.get()`)
- `db.scalars().all()` stays the same
- `/start` removes `asyncio.create_task(run())` — direct await instead

- [ ] **Step 1: Write `backend/routes/workflows.py`**

```python
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import AsyncSessionLocal, get_db
from backend.models import (
    AgentRun,
    EventLog,
    Store,
    WorkflowInstance,
    WorkflowState,
)
from backend.orchestrator.engine import WorkflowEngine
from backend.schemas import (
    AgentRunResponse,
    EventLogResponse,
    TimelineResponse,
    WorkflowStatusResponse,
)

router = APIRouter()


@router.get("/{store_id}", response_model=StoreResponse)
async def get_store_detail(
    store_id: int,
    db: AsyncSession = Depends(get_db),
) -> StoreResponse:
    """Get store details."""
    store = await db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.post("/{store_id}/start")
async def start_workflow(
    store_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    """Start the workflow for a store."""
    store = await db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    async with AsyncSessionLocal() as session:
        eng = WorkflowEngine(session)
        try:
            await eng.run_workflow(store)
            await session.commit()
        except Exception as e:
            from backend.logging_config import get_logger
            logger = get_logger(__name__)
            logger.error(f"Workflow error for store {store_id}: {e}", exc_info=True)
            await session.rollback()
            raise

    return {"message": "Workflow started", "store_id": store_id}


@router.get("/{store_id}/status", response_model=WorkflowStatusResponse)
async def get_status(
    store_id: int,
    db: AsyncSession = Depends(get_db),
) -> WorkflowStatusResponse:
    """Query store current state and recent agent runs."""
    store = await db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    stmt = select(WorkflowInstance).where(WorkflowInstance.store_id == store_id)
    result = await db.execute(stmt)
    wf = result.scalar_one_or_none()

    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    recent_runs_stmt = (
        select(AgentRun)
        .where(AgentRun.store_id == store_id)
        .order_by(AgentRun.created_at.desc())
        .limit(10)
    )
    result = await db.execute(recent_runs_stmt)
    recent_runs = list(result.scalars().all())

    return WorkflowStatusResponse(
        store_id=store.id,
        store_name=store.name,
        current_state=wf.current_state,
        consecutive_failures=wf.consecutive_failures,
        retry_count=wf.retry_count,
        started_at=wf.started_at,
        recent_agent_runs=[
            AgentRunResponse(
                id=r.id,
                agent_type=r.agent_type,
                status=r.status,
                state_at_run=r.state_at_run,
                output_data=r.output_data or {},
                error_msg=r.error_msg,
                retry_count=r.retry_count,
                duration_ms=r.duration_ms,
                created_at=r.created_at,
            )
            for r in recent_runs
        ],
    )


@router.get("/{store_id}/timeline", response_model=TimelineResponse)
async def get_timeline(
    store_id: int,
    db: AsyncSession = Depends(get_db),
) -> TimelineResponse:
    """Query store event timeline."""
    store = await db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    stmt_wf = select(WorkflowInstance).where(WorkflowInstance.store_id == store_id)
    result = await db.execute(stmt_wf)
    wf = result.scalar_one_or_none()
    current_state = wf.current_state if wf else "NEW_STORE"

    events_stmt = (
        select(EventLog)
        .where(EventLog.store_id == store_id)
        .order_by(EventLog.created_at.desc())
        .limit(100)
    )
    result = await db.execute(events_stmt)
    events = list(result.scalars().all())

    return TimelineResponse(
        store_id=store.id,
        store_name=store.name,
        current_state=current_state,
        events=[
            EventLogResponse(
                id=e.id,
                event_type=e.event_type,
                from_state=e.from_state,
                to_state=e.to_state,
                agent_type=e.agent_type,
                message=e.message,
                extra_data=e.extra_data or {},
                created_at=e.created_at,
            )
            for e in events
        ],
    )


@router.post("/{store_id}/manual-takeover")
async def manual_takeover(
    store_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    """Trigger manual takeover for a store."""
    store = await db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    eng = WorkflowEngine(db)
    await eng.trigger_manual_takeover(store)
    await db.commit()

    return {"message": "Manual takeover triggered", "store_id": store_id}
```

**Note:** `StoreResponse` is referenced but not imported. Add it to the imports:
```python
from backend.schemas import (
    AgentRunResponse,
    EventLogResponse,
    StoreResponse,
    TimelineResponse,
    WorkflowStatusResponse,
)
```

- [ ] **Step 2: Run lint**

Run: `cd backend && uv run ruff check routes/workflows.py`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add backend/routes/workflows.py
git commit -m "feat(routes): split workflow routes into routes/workflows.py

- GET /stores/{id}, POST /start, GET /status, GET /timeline, POST /manual-takeover
- All async with AsyncSession
- /start: direct await instead of asyncio.create_task"
```

---

## Task 3: Create `routes/dashboard.py` and `routes/alerts.py`

**Files:**
- Create: `backend/routes/dashboard.py`
- Create: `backend/routes/alerts.py`
- Read: `backend/main.py` lines 220-334 (dashboard + alerts)

- [ ] **Step 1: Write `backend/routes/dashboard.py`**

```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.models import AgentRun, Alert, Store, WorkflowInstance, WorkflowState
from backend.schemas import DashboardSummaryResponse

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
) -> DashboardSummaryResponse:
    """Global overview: state distribution, anomalies, queue backlog."""
    # Total stores
    result = await db.execute(select(func.count(Store.id)))
    total = result.scalar() or 0

    # State distribution
    state_dist: dict[str, int] = {}
    result = await db.execute(select(WorkflowInstance))
    wfs = result.scalars().all()
    for wf in wfs:
        state_dist[wf.current_state] = state_dist.get(wf.current_state, 0) + 1

    # Anomaly count (non-acknowledged alerts)
    result = await db.execute(
        select(func.count(Alert.id)).where(Alert.acknowledged == 0)
    )
    anomaly_count = result.scalar() or 0

    # Manual review queue
    result = await db.execute(
        select(WorkflowInstance, Store)
        .join(Store, WorkflowInstance.store_id == Store.id)
        .where(WorkflowInstance.current_state == WorkflowState.MANUAL_REVIEW.value)
    )
    rows = result.all()
    manual_review_queue = [
        {"store_id": wf.store_id, "store_name": s.name, "state": wf.current_state}
        for wf, s in rows
    ]

    # Recent alerts
    result = await db.execute(
        select(Alert, Store)
        .join(Store, Alert.store_id == Store.id)
        .order_by(Alert.created_at.desc())
        .limit(20)
    )
    alert_rows = result.all()
    recent_alerts = [
        {
            "id": a.id,
            "store_id": a.store_id,
            "store_name": s.name,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "message": a.message,
            "acknowledged": bool(a.acknowledged),
            "created_at": a.created_at.isoformat(),
        }
        for a, s in alert_rows
    ]

    # Recent agent runs
    result = await db.execute(
        select(AgentRun, Store)
        .join(Store, AgentRun.store_id == Store.id)
        .order_by(AgentRun.created_at.desc())
        .limit(20)
    )
    run_rows = result.all()
    recent_runs = [
        {
            "id": r.id,
            "store_id": r.store_id,
            "store_name": s.name,
            "agent_type": r.agent_type,
            "status": r.status,
            "duration_ms": r.duration_ms,
            "created_at": r.created_at.isoformat(),
        }
        for r, s in run_rows
    ]

    return DashboardSummaryResponse(
        total_stores=total,
        state_distribution=state_dist,
        anomaly_count=anomaly_count,
        manual_review_queue=manual_review_queue,
        recent_alerts=recent_alerts,
        recent_agent_runs=recent_runs,
    )
```

- [ ] **Step 2: Write `backend/routes/alerts.py`**

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Alert, Store

router = APIRouter()


@router.get("")
async def list_alerts(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """List all alerts."""
    result = await db.execute(
        select(Alert, Store)
        .join(Store, Alert.store_id == Store.id)
        .order_by(Alert.created_at.desc())
        .limit(100)
    )
    rows = result.all()
    return [
        {
            "id": a.id,
            "store_id": a.store_id,
            "store_name": s.name,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "message": a.message,
            "acknowledged": bool(a.acknowledged),
            "created_at": a.created_at.isoformat(),
        }
        for a, s in rows
    ]


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    """Acknowledge an alert."""
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = 1
    await db.flush()
    await db.commit()
    return {"message": "Alert acknowledged", "alert_id": alert_id}
```

- [ ] **Step 3: Update `routes/__init__.py` with new routers**

Add to `backend/routes/__init__.py`:
```python
from .dashboard import router as dashboard_router
from .alerts import router as alerts_router
```

- [ ] **Step 4: Run lint**

Run: `cd backend && uv run ruff check routes/`
Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add backend/routes/dashboard.py backend/routes/alerts.py backend/routes/__init__.py
git commit -m "feat(routes): split dashboard and alerts into routes/

- routes/dashboard.py — GET /dashboard/summary
- routes/alerts.py — GET /alerts, POST /alerts/{id}/acknowledge
- All async with AsyncSession"
```

---

## Task 4: Rewrite `main.py` — router registration only

**Files:**
- Rewrite: `backend/main.py`
- Read: `backend/main.py` (current full file)

- [ ] **Step 1: Write the new `backend/main.py`**

Replace the entire content of `backend/main.py` with:

```python
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.logging_config import get_logger, setup_logging
from backend.migrations import MigrationRunner
from backend.database import async_engine
from backend.routes import (
    alerts_router,
    dashboard_router,
    stores_router,
    workflows_router,
)

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Running pending migrations...")
    runner = MigrationRunner(async_engine)
    applied = await runner.run_pending()
    if applied:
        logger.info(f"Migrations applied: {applied}")
    else:
        logger.info("No pending migrations")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Multi-Agent Ops API",
    description="Multi-agent operations system for local life services",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stores_router, prefix="/stores", tags=["stores"])
app.include_router(workflows_router, prefix="/stores", tags=["workflows"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
app.include_router(alerts_router, prefix="/alerts", tags=["alerts"])


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}
```

**Changes from old main.py:**
- All route handlers removed (now in `routes/`)
- `main.py` now only: app definition, middleware, router registration, lifespan, `/health`
- Removed `BackgroundTasks` from imports (no longer used)
- Removed all `from backend.database import ...` except `async_engine`
- Removed all `from backend.models import ...` imports (not needed in main.py anymore)
- Removed all `from backend.schemas import ...` imports (not needed in main.py anymore)
- Removed `init_db` import

- [ ] **Step 2: Run tests**

Run: `cd backend && uv run pytest ../tests/ -v`
Expected: 16/16 PASS

- [ ] **Step 3: Run lint**

Run: `cd backend && uv run ruff check main.py`
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add backend/main.py
git commit -m "refactor(main): strip to router registration only

- All 12 route handlers moved to routes/ modules
- main.py now: app + lifespan (migrations) + router registration + /health"
```

---

## Task 5: Convert `WorkflowEngine` to full async

**Files:**
- Rewrite: `backend/orchestrator/engine.py`
- Read: `backend/orchestrator/engine.py` (current full file)

This is the most critical conversion. Every `db.execute()` becomes `await db.execute()`. All `self.db.add()`, `self.db.flush()` etc. remain sync (add/flush are sync in SQLAlchemy).

**Additional P1 fixes in this task:**
- `AgentRun.retry_count` now tracks actual retry attempts from `run_with_retry`
- Remove redundant `failure_rate` in `_run_agent` (already stored in agent instance)

- [ ] **Step 1: Write the new `backend/orchestrator/engine.py`**

```python
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.analyzer import AnalyzerAgent
from backend.agents.base import AgentResult, AgentStatus as AgentResultStatus
from backend.agents.mobile_operator import MobileOperatorAgent
from backend.agents.reporter import ReporterAgent
from backend.agents.web_operator import WebOperatorAgent
from backend.logging_config import get_logger
from backend.models import (
    VALID_TRANSITIONS,
    AgentRun,
    Alert,
    EventLog,
    Report,
    Store,
    WorkflowInstance,
    WorkflowState,
)

logger = get_logger(__name__)


class WorkflowEngine:
    """
    Orchestrates the multi-agent workflow for a single store.
    Handles state transitions, agent execution, retry logic, and event logging.
    """

    MAX_RETRIES = 3
    STATES_REQUIRING_ANALYZER = {WorkflowState.DIAGNOSIS}
    STATES_REQUIRING_WEB_OPS = {WorkflowState.FOUNDATION, WorkflowState.DAILY_OPS}
    STATES_REQUIRING_MOBILE_OPS = {WorkflowState.DAILY_OPS}
    STATES_REQUIRING_REPORTER = {WorkflowState.WEEKLY_REPORT}

    def __init__(self, db: AsyncSession):
        self.db = db
        self.analyzer = AnalyzerAgent()
        self.web_operator = WebOperatorAgent(failure_rate=0.2)
        self.mobile_operator = MobileOperatorAgent(failure_rate=0.25)
        self.reporter = ReporterAgent()

    async def get_or_create_workflow(self, store: Store) -> WorkflowInstance:
        """Get existing workflow or create a new one for the store."""
        stmt = select(WorkflowInstance).where(WorkflowInstance.store_id == store.id)
        result = await self.db.execute(stmt)
        wf = result.scalar_one_or_none()
        if wf is None:
            wf = WorkflowInstance(
                store_id=store.id,
                current_state=WorkflowState.NEW_STORE.value,
                consecutive_failures=0,
                retry_count=0,
                started_at=datetime.now(UTC),
            )
            self.db.add(wf)
            await self.db.flush()
            await self._log_event(
                store_id=store.id,
                event_type="workflow_created",
                message=f"Workflow created for store {store.store_id}",
                extra_data={"initial_state": wf.current_state},
            )
            logger.info(f"Created workflow for store {store.store_id}")
        return wf

    async def run_workflow(self, store: Store) -> WorkflowInstance:
        """
        Execute the full workflow for a store.
        Runs agents based on current state, handles transitions, and manages failures.
        """
        wf = await self.get_or_create_workflow(store)
        state = WorkflowState(wf.current_state)

        logger.info(f"Starting workflow for store {store.store_id}, state={state.value}")

        if state == WorkflowState.DONE:
            logger.info("Store already DONE, skipping")
            return wf

        # Determine which agents to run in this state
        agents_to_run = self._get_agents_for_state(state)

        # Build context
        context: dict = {
            "store_id": store.store_id,
            "store_data": self._store_to_dict(store),
            "workflow_state": state.value,
        }

        # Run agents and collect results
        any_failure = False

        for agent_type in agents_to_run:
            context, result = await self._run_agent(agent_type, context, wf)
            # PERSIST: pass actual retry count from result
            await self._persist_agent_run(store.id, agent_type, context, result, state)

            if result.status != AgentResultStatus.SUCCESS:
                any_failure = True
                break

        # Determine next state
        if any_failure:
            wf.consecutive_failures += 1
            if wf.consecutive_failures >= self.MAX_RETRIES:
                next_state = WorkflowState.MANUAL_REVIEW
                await self._create_alert(
                    store_id=store.id,
                    alert_type="consecutive_failure",
                    severity="critical",
                    message=f"连续{self.MAX_RETRIES}次失败，触发人工接管",
                    extra_data={"failures": wf.consecutive_failures},
                )
                logger.warning(
                    f"Store {store.store_id}: consecutive failures "
                    f"{wf.consecutive_failures} -> MANUAL_REVIEW"
                )
            else:
                next_state = state
                logger.warning(
                    f"Store {store.store_id}: failure in {state.value}, "
                    f"retry {wf.consecutive_failures}/{self.MAX_RETRIES - 1}"
                )
        else:
            wf.consecutive_failures = 0
            next_state = self._get_next_state(state)
            logger.info(
                f"Store {store.store_id}: {state.value} completed, "
                f"transitioning to {next_state.value}"
            )

        # Transition state
        if next_state != state:
            await self._transition_state(store.id, wf, state, next_state)

        # Generate report if entering WEEKLY_REPORT
        if next_state == WorkflowState.WEEKLY_REPORT:
            await self._generate_report(store, context, "weekly")

        wf.updated_at = datetime.now(UTC)
        self.db.add(wf)
        await self.db.flush()
        return wf

    async def _run_agent(
        self, agent_type: str, context: dict, wf: WorkflowInstance
    ) -> tuple[dict, AgentResult]:
        """Run a specific agent with context."""
        agent_map: dict[str, AnalyzerAgent | MobileOperatorAgent | ReporterAgent | WebOperatorAgent] = {
            "analyzer": self.analyzer,
            "web_operator": self.web_operator,
            "mobile_operator": self.mobile_operator,
            "reporter": self.reporter,
        }

        agent = agent_map.get(agent_type)
        if agent is None:
            return context, AgentResult(
                agent_type=agent_type,
                status=AgentResultStatus.FAILED,
                error=f"Unknown agent type: {agent_type}",
            )

        logger.info(f"Running agent {agent_type} for {context.get('store_id')}")

        # Use agent's own failure_rate (no redundant parameter)
        result = await agent.run_with_retry(
            context,
            max_retries=self.MAX_RETRIES,
        )

        # Update context with agent output
        if result.data:
            context[agent_type] = result.data
            if agent_type == "analyzer":
                context["diagnosis"] = result.data

        return context, result

    def _get_agents_for_state(self, state: WorkflowState) -> list[str]:
        """Return list of agent types to run for a given state."""
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

    def _get_next_state(self, current: WorkflowState) -> WorkflowState:
        """Get the next state in the happy path."""
        next_map: dict[WorkflowState, WorkflowState] = {
            WorkflowState.NEW_STORE: WorkflowState.DIAGNOSIS,
            WorkflowState.DIAGNOSIS: WorkflowState.FOUNDATION,
            WorkflowState.FOUNDATION: WorkflowState.DAILY_OPS,
            WorkflowState.DAILY_OPS: WorkflowState.WEEKLY_REPORT,
            WorkflowState.WEEKLY_REPORT: WorkflowState.DONE,
        }
        return next_map.get(current, current)

    async def _transition_state(
        self,
        store_id: int,
        wf: WorkflowInstance,
        from_state: WorkflowState,
        to_state: WorkflowState,
    ) -> None:
        """Transition workflow to a new state with validation."""
        valid = VALID_TRANSITIONS.get(from_state, set())
        if to_state not in valid and to_state != WorkflowState.MANUAL_REVIEW:
            logger.error(f"Invalid transition: {from_state.value} -> {to_state.value}")
            return

        old_state = wf.current_state
        wf.current_state = to_state.value
        self.db.add(wf)
        await self.db.flush()

        await self._log_event(
            store_id=store_id,
            event_type="state_change",
            from_state=from_state.value,
            to_state=to_state.value,
            message=f"State transition: {old_state} -> {to_state.value}",
        )
        logger.info(f"Store {store_id}: transitioned {from_state.value} -> {to_state.value}")

    async def _generate_report(
        self, store: Store, context: dict, report_type: str
    ) -> None:
        """Generate and persist a report."""
        report_context: dict = {
            **context,
            "store_id": store.store_id,
            "store_data": self._store_to_dict(store),
            "report_type": report_type,
        }

        result = await self.reporter.execute(report_context)

        if result.status == AgentResultStatus.SUCCESS:
            report = Report(
                store_id=store.id,
                report_type=report_type,
                content_md=result.data.get("md_report"),
                content_json=result.data.get("json_report"),
            )
            self.db.add(report)
            await self.db.flush()
            await self._log_event(
                store_id=store.id,
                event_type="report_generated",
                message=f"{report_type} report generated",
                extra_data={"report_id": report.id},
            )
            logger.info(f"Report generated for store {store.store_id}")

    async def _persist_agent_run(
        self,
        store_id: int,
        agent_type: str,
        context: dict,
        result: AgentResult,
        state: WorkflowState,
    ) -> None:
        """Persist an agent run record. P1 fix: uses actual retry_count from result."""
        # P1 FIX: count retries from the result metadata
        # The base agent's run_with_retry doesn't currently track attempts,
        # so we record 0 and add a comment noting this limitation.
        # To fully fix: base agent's run_with_retry should return attempt count.
        retry_count = getattr(result, "retry_count", 0) or 0

        run = AgentRun(
            store_id=store_id,
            agent_type=agent_type,
            status=result.status.value,
            state_at_run=state.value,
            input_data={"store_data": context.get("store_data", {})},
            output_data=result.data or {},
            error_msg=result.error,
            retry_count=retry_count,
            duration_ms=result.duration_ms,
        )
        self.db.add(run)
        await self.db.flush()

        await self._log_event(
            store_id=store_id,
            event_type="agent_run",
            agent_type=agent_type,
            message=f"{agent_type} {result.status.value} ({result.duration_ms}ms)",
            extra_data={"run_id": run.id, "error": result.error},
        )

    async def _log_event(
        self,
        store_id: int,
        event_type: str,
        from_state: str | None = None,
        to_state: str | None = None,
        agent_type: str | None = None,
        message: str | None = None,
        extra_data: dict | None = None,
    ) -> None:
        """Create a structured event log entry."""
        event = EventLog(
            store_id=store_id,
            event_type=event_type,
            from_state=from_state,
            to_state=to_state,
            agent_type=agent_type,
            message=message,
            extra_data=extra_data or {},
        )
        self.db.add(event)

    async def _create_alert(
        self,
        store_id: int,
        alert_type: str,
        severity: str,
        message: str,
        extra_data: dict | None = None,
    ) -> None:
        """Create an alert for anomalies."""
        alert = Alert(
            store_id=store_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            extra_data=extra_data or {},
        )
        self.db.add(alert)

    async def trigger_manual_takeover(self, store: Store) -> WorkflowInstance:
        """Move a store to MANUAL_REVIEW state."""
        wf = await self.get_or_create_workflow(store)
        old_state = WorkflowState(wf.current_state)

        wf.current_state = WorkflowState.MANUAL_REVIEW.value
        wf.consecutive_failures = 0
        wf.updated_at = datetime.now(UTC)
        self.db.add(wf)
        await self.db.flush()

        await self._log_event(
            store_id=store.id,
            event_type="manual_takeover",
            from_state=old_state.value,
            to_state=WorkflowState.MANUAL_REVIEW.value,
            message="Manual takeover triggered",
        )
        await self._create_alert(
            store_id=store.id,
            alert_type="manual_takeover",
            severity="warning",
            message="人工接管已触发",
        )
        logger.info(f"Manual takeover triggered for store {store.store_id}")
        return wf

    def _store_to_dict(self, store: Store) -> dict:
        """Convert Store model to dict for agents."""
        return {
            "store_id": store.store_id,
            "name": store.name,
            "city": store.city,
            "category": store.category,
            "rating": store.rating,
            "monthly_orders": store.monthly_orders,
            "gmv_last_7d": store.gmv_last_7d,
            "review_count": store.review_count,
            "review_reply_rate": store.review_reply_rate,
            "ros_health": store.ros_health,
            "competitor_avg_discount": store.competitor_avg_discount,
            "issues": store.issues or [],
        }
```

- [ ] **Step 2: Update imports in `agents/base.py`**

Verify `backend/agents/base.py` no longer has `AgentStatus` (it was removed in Plan 2's Task 5). Add import if missing:
```python
from backend.models import AgentStatus
```

- [ ] **Step 3: Run tests**

Run: `cd backend && uv run pytest ../tests/ -v`
Expected: 16/16 PASS

- [ ] **Step 4: Run lint**

Run: `cd backend && uv run ruff check .`
Expected: All checks passed

- [ ] **Step 5: Format**

Run: `cd backend && uv run ruff format .`

- [ ] **Step 6: Commit**

```bash
git add backend/orchestrator/engine.py backend/agents/base.py
git commit -m "feat(engine): fully async WorkflowEngine

- All db.execute() -> await db.execute()
- All engine methods async def
- Removed redundant failure_rate parameter
- P1 fix: retry_count tracking stub (full fix needs base agent change)"
```

---

## Task 6: Fix `retry_count` tracking in base agent

**Files:**
- Modify: `backend/agents/base.py`
- Read: `backend/agents/base.py`

**Files:**
- Modify: `backend/agents/base.py`

- [ ] **Step 1: Update `AgentResult` dataclass to include attempt count**

Add `attempts` field to `AgentResult`:

```python
@dataclass
class AgentResult:
    agent_type: str
    status: AgentStatus
    data: dict | None = None
    error: str | None = None
    duration_ms: int = 0
    attempts: int = 1  # P1 FIX: track number of attempts made
```

- [ ] **Step 2: Update `run_with_retry` to count attempts**

In the `run_with_retry` method, add `attempts = attempt + 1` to each result:

```python
for attempt in range(max_retries):
    ...
    if failure_rate > 0 and random.random() < failure_rate:
        ...
        last_result = AgentResult(
            ...
            attempts=attempt + 1,  # count this attempt
        )
        ...

    try:
        result = await self.execute(context)
        duration_ms = int((time.perf_counter() - start) * 1000)
        result.duration_ms = duration_ms
        result.attempts = attempt + 1  # P1 FIX: record attempt count
        last_result = result
        ...

    except Exception as e:
        ...
        last_result = AgentResult(
            ...
            attempts=attempt + 1,  # count this attempt
        )
```

Also update the final fallback result:
```python
return last_result or AgentResult(
    agent_type=self.agent_type,
    status=AgentStatus.FAILED,
    error="Max retries exceeded",
    attempts=max_retries,
)
```

- [ ] **Step 3: Update `engine.py` `_persist_agent_run` to use `result.attempts`**

In `backend/orchestrator/engine.py`, change:
```python
retry_count = getattr(result, "retry_count", 0) or 0
```
To:
```python
retry_count = result.attempts - 1  # P1 FIX: attempts - 1 = number of retries made
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest ../tests/ -v`
Expected: 16/16 PASS

- [ ] **Step 5: Run lint**

Run: `cd backend && uv run ruff check .`
Expected: All checks passed

- [ ] **Step 6: Commit**

```bash
git add backend/agents/base.py backend/orchestrator/engine.py
git commit -m "fix(engine): track actual retry attempts in AgentResult

- AgentResult now includes attempts field
- run_with_retry sets attempts = attempt + 1 for each result
- _persist_agent_run reads result.attempts for retry_count
- P1: AgentRun.retry_count now reflects actual retry attempts"
```

---

## Verification

1. `make backend-test` — 16/16 PASS
2. `make backend-lint` — All checks passed
3. `make backend-fmt` — formatted
4. `make backend-migrate` — applies migrations
5. `make backend-dev` — starts without errors, `/health` returns `{"status": "ok"}`
6. `curl http://localhost:8000/stores` — returns `[]` (empty store list)
7. Manual smoke test:
   - `POST /stores/import` with mock data
   - `GET /stores` shows imported store
   - `POST /stores/1/start` starts workflow (verify DB records)
   - `GET /stores/1/status` shows workflow state
   - `GET /dashboard/summary` shows summary
