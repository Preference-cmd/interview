from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import async_engine
from backend.logging_config import get_logger, setup_logging
from backend.migrations import MigrationRunner
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
