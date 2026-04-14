import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from backend.database import engine, get_db, init_db, AsyncSessionLocal
from backend.models import Store, WorkflowInstance, AgentRun, EventLog, Alert, Report, WorkflowState
from backend.schemas import (
    StoreImportRequest,
    StoreImportItem,
    StoreResponse,
    WorkflowStatusResponse,
    AgentRunResponse,
    TimelineResponse,
    EventLogResponse,
    DashboardSummaryResponse,
)
from backend.orchestrator.engine import WorkflowEngine
from backend.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized")
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


# --- Health ---
@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# --- Stores ---
@app.post("/stores/import", response_model=list[StoreResponse])
async def import_stores(request: StoreImportRequest, db: Session = Depends(get_db)):
    """Batch import store data."""
    imported = []
    for item in request.stores:
        stmt = select(Store).where(Store.store_id == item.store_id)
        existing = db.execute(stmt).scalar_one_or_none()
        if existing:
            # Update existing
            for field, value in item.model_dump().items():
                if field != "store_id":
                    setattr(existing, field, value)
            existing.updated_at = datetime.utcnow()
            imported.append(existing)
        else:
            store = Store(**item.model_dump())
            db.add(store)
            imported.append(store)
    db.flush()
    logger.info(f"Imported {len(imported)} stores")
    return imported


@app.get("/stores", response_model=list[StoreResponse])
async def list_stores(db: Session = Depends(get_db)):
    """List all stores."""
    stmt = select(Store).order_by(Store.created_at.desc())
    return db.execute(stmt).scalars().all()


@app.get("/stores/{store_id}", response_model=StoreResponse)
async def get_store(store_id: int, db: Session = Depends(get_db)):
    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@app.post("/stores/{store_id}/start")
async def start_workflow(store_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Start the workflow for a store."""
    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    # Run workflow in background to avoid timeout
    async def run():
        async with AsyncSessionLocal() as session:
            eng = WorkflowEngine(session)
            try:
                await eng.run_workflow(store)
                await session.commit()
            except Exception as e:
                logger.error(f"Workflow error for store {store_id}: {e}", exc_info=True)
                await session.rollback()

    asyncio.create_task(run())
    return {"message": "Workflow started", "store_id": store_id}


@app.get("/stores/{store_id}/status", response_model=WorkflowStatusResponse)
async def get_status(store_id: int, db: Session = Depends(get_db)):
    """Query store current state and recent agent runs."""
    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    stmt = select(WorkflowInstance).where(WorkflowInstance.store_id == store_id)
    wf = db.execute(stmt).scalar_one_or_none()

    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    recent_runs_stmt = (
        select(AgentRun)
        .where(AgentRun.store_id == store_id)
        .order_by(AgentRun.created_at.desc())
        .limit(10)
    )
    recent_runs = db.execute(recent_runs_stmt).scalars().all()

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


@app.get("/stores/{store_id}/timeline", response_model=TimelineResponse)
async def get_timeline(store_id: int, db: Session = Depends(get_db)):
    """Query store event timeline."""
    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    stmt_wf = select(WorkflowInstance).where(WorkflowInstance.store_id == store_id)
    wf = db.execute(stmt_wf).scalar_one_or_none()
    current_state = wf.current_state if wf else "NEW_STORE"

    events_stmt = (
        select(EventLog)
        .where(EventLog.store_id == store_id)
        .order_by(EventLog.created_at.desc())
        .limit(100)
    )
    events = db.execute(events_stmt).scalars().all()

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


@app.post("/stores/{store_id}/manual-takeover")
async def manual_takeover(store_id: int, db: Session = Depends(get_db)):
    """Trigger manual takeover for a store."""
    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    eng = WorkflowEngine(db)
    eng.trigger_manual_takeover(store)
    db.commit()

    return {"message": "Manual takeover triggered", "store_id": store_id}


# --- Dashboard ---
@app.get("/dashboard/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(db: Session = Depends(get_db)):
    """Global overview: state distribution, anomalies, queue backlog."""
    # Total stores
    total = db.execute(select(func.count(Store.id))).scalar()

    # State distribution
    state_dist = {}
    wfs = db.execute(select(WorkflowInstance)).scalars().all()
    for wf in wfs:
        state_dist[wf.current_state] = state_dist.get(wf.current_state, 0) + 1

    # Anomaly count (non-acknowledged alerts)
    anomaly_count = db.execute(
        select(func.count(Alert.id)).where(Alert.acknowledged == 0)
    ).scalar()

    # Manual review queue
    manual_review_stores = db.execute(
        select(WorkflowInstance, Store)
        .join(Store, WorkflowInstance.store_id == Store.id)
        .where(WorkflowInstance.current_state == WorkflowState.MANUAL_REVIEW.value)
    ).all()
    manual_review_queue = [
        {"store_id": wf.store_id, "store_name": s.name, "state": wf.current_state}
        for wf, s in manual_review_stores
    ]

    # Recent alerts
    recent_alerts_stmt = (
        select(Alert, Store)
        .join(Store, Alert.store_id == Store.id)
        .order_by(Alert.created_at.desc())
        .limit(20)
    )
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
        for a, s in db.execute(recent_alerts_stmt).all()
    ]

    # Recent agent runs
    recent_runs_stmt = (
        select(AgentRun, Store)
        .join(Store, AgentRun.store_id == Store.id)
        .order_by(AgentRun.created_at.desc())
        .limit(20)
    )
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
        for r, s in db.execute(recent_runs_stmt).all()
    ]

    return DashboardSummaryResponse(
        total_stores=total or 0,
        state_distribution=state_dist,
        anomaly_count=anomaly_count or 0,
        manual_review_queue=manual_review_queue,
        recent_alerts=recent_alerts,
        recent_agent_runs=recent_runs,
    )


# --- Alerts ---
@app.get("/alerts", response_model=list[dict])
async def list_alerts(db: Session = Depends(get_db)):
    """List all alerts."""
    stmt = (
        select(Alert, Store)
        .join(Store, Alert.store_id == Store.id)
        .order_by(Alert.created_at.desc())
        .limit(100)
    )
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
        for a, s in db.execute(stmt).all()
    ]


@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    """Acknowledge an alert."""
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = 1
    db.add(alert)
    db.flush()
    return {"message": "Alert acknowledged", "alert_id": alert_id}
