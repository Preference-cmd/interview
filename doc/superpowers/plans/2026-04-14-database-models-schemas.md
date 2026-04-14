# Database + Models + Schemas Modularization Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split monolithic `backend/models.py` and `backend/schemas.py` into focused modules, and create a proper async database layer replacing the current sync/async hybrid. After this plan, all model and schema imports use the new paths; `backend/models.py` and `backend/schemas.py` are deleted.

**Architecture:** Each SQLAlchemy model gets its own file under `backend/models/`. Enums and the state transition map go into `backend/models/_enums.py`. Pydantic schemas are split by domain. The database layer uses `create_async_engine` + `async_sessionmaker` from SQLAlchemy 2.x. Old `database.py` becomes a re-export shim.

**Tech Stack:** SQLAlchemy 2.x async, aiosqlite, Pydantic v2

---

## File Map

```
backend/
├── database/
│   ├── __init__.py        ← re-exports: async_engine, AsyncSessionLocal, get_db
│   └── session.py         ← async engine + session maker + get_db (replaces database.py)
├── models/
│   ├── __init__.py        ← unified exports: all models + enums + VALID_TRANSITIONS
│   ├── _enums.py          ← WorkflowState, AgentStatus, VALID_TRANSITIONS
│   ├── store.py           ← Store
│   ├── workflow.py         ← WorkflowInstance
│   ├── agent_run.py        ← AgentRun
│   ├── event_log.py        ← EventLog
│   ├── alert.py            ← Alert
│   └── report.py           ← Report
├── schemas/
│   ├── __init__.py        ← unified exports
│   ├── store.py           ← StoreImportRequest/Item + StoreResponse
│   ├── workflow.py         ← WorkflowStatusResponse
│   ├── agent.py           ← AgentRunResponse
│   ├── timeline.py        ← EventLogResponse + TimelineResponse
│   ├── dashboard.py       ← DashboardSummaryResponse
│   └── alert.py           ← AlertResponse
├── main.py                ← update imports to use new paths
├── orchestrator/engine.py ← update imports
└── agents/
    ├── base.py             ← update imports
    └── *.py               ← update imports
```

---

## Task 1: Create async database layer

**Files:**
- Create: `backend/database/__init__.py`
- Create: `backend/database/session.py`
- Read: `backend/database.py` (current sync implementation)

- [ ] **Step 1: Write `backend/database/session.py`**

```python
from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./multi_agent_ops.db")

async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db():
    """Dependency for FastAPI routes to get async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 2: Write `backend/database/__init__.py`**

```python
from .session import async_engine, AsyncSessionLocal, get_db

__all__ = ["async_engine", "AsyncSessionLocal", "get_db"]
```

- [ ] **Step 3: Replace `backend/database.py` content**

Write the new content of `backend/database.py`:

```python
"""
Legacy import shim. New code should import from backend.database instead.
"""
from .session import async_engine, AsyncSessionLocal, get_db

__all__ = ["async_engine", "AsyncSessionLocal", "get_db"]
```

- [ ] **Step 4: Run lint**

Run: `cd backend && uv run ruff check database/ database.py`
Expected: no errors

- [ ] **Step 5: Format**

Run: `cd backend && uv run ruff format database/ database.py`

- [ ] **Step 6: Commit**

```bash
git add backend/database/
git add backend/database.py
git commit -m "refactor(db): create async database layer

- database/session.py — create_async_engine + async_sessionmaker
- database/__init__.py — unified exports
- database.py — legacy shim re-exporting from session.py"
```

---

## Task 2: Extract enums to `models/_enums.py`

**Files:**
- Create: `backend/models/__init__.py`
- Create: `backend/models/_enums.py`
- Read: `backend/models.py` (lines 1-36, the enums and VALID_TRANSITIONS)

- [ ] **Step 1: Write `backend/models/_enums.py`**

```python
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


VALID_TRANSITIONS: dict[WorkflowState, set[WorkflowState]] = {
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
```

- [ ] **Step 2: Write `backend/models/__init__.py`**

```python
from __future__ import annotations

from ._enums import VALID_TRANSITIONS
from ._enums import AgentStatus
from ._enums import WorkflowState
from .alert import Alert
from .agent_run import AgentRun
from .event_log import EventLog
from .report import Report
from .store import Store
from .workflow import WorkflowInstance

__all__ = [
    "AgentStatus",
    "Alert",
    "AgentRun",
    "EventLog",
    "Report",
    "Store",
    "VALID_TRANSITIONS",
    "WorkflowInstance",
    "WorkflowState",
]
```

- [ ] **Step 3: Run tests**

Run: `cd backend && uv run pytest ../tests/ -v`
Expected: 16/16 PASS (models are loaded via SQLAlchemy ORM, no change in behavior)

- [ ] **Step 4: Run lint**

Run: `cd backend && uv run ruff check models/`
Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add backend/models/
git commit -m "refactor(models): split enums into models/_enums.py

- models/_enums.py — WorkflowState, AgentStatus, VALID_TRANSITIONS
- models/__init__.py — unified exports
- Old models.py imports still work via the remaining models below"
```

---

## Task 3: Split models into individual files

**Files:**
- Create: `backend/models/store.py`
- Create: `backend/models/workflow.py`
- Create: `backend/models/agent_run.py`
- Create: `backend/models/event_log.py`
- Create: `backend/models/alert.py`
- Create: `backend/models/report.py`
- Read: `backend/models.py` (current full file)

Read the current `backend/models.py` to extract each model. The current file has:
- Lines 38-63: Store
- Lines 66-81: WorkflowInstance
- Lines 84-104: AgentRun
- Lines 107-124: EventLog
- Lines 127-143: Alert
- Lines 146-160: Report

**Important:** Remove `__table_args__ = {"extend_existing": True}` from all models — the migration SQL uses `IF NOT EXISTS` so this is no longer needed.

- [ ] **Step 1: Write `backend/models/store.py`**

```python
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String
from sqlalchemy.orm import relationship

from backend.database import Base


class Store(Base):
    __tablename__ = "stores"

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
```

- [ ] **Step 2: Write `backend/models/workflow.py`**

```python
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.database import Base
from backend.models._enums import WorkflowState


class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"
    __table_args__ = (
        UniqueConstraint("store_id", name="uq_workflow_store_id"),
        Index("ix_workflow_instances_current_state", "current_state"),
    )

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    current_state = Column(String(32), default=WorkflowState.NEW_STORE.value, index=True)
    consecutive_failures = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    store = relationship("Store", back_populates="workflow")
```

- [ ] **Step 3: Write `backend/models/agent_run.py`**

```python
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base
from backend.models._enums import AgentStatus


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (Index("ix_agent_runs_store_created", "store_id", "created_at"),)

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
```

- [ ] **Step 4: Write `backend/models/event_log.py`**

```python
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class EventLog(Base):
    __tablename__ = "event_logs"
    __table_args__ = (Index("ix_event_logs_store_created", "store_id", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    from_state = Column(String(32), nullable=True)
    to_state = Column(String(32), nullable=True)
    agent_type = Column(String(64), nullable=True)
    message = Column(Text)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.now(UTC), index=True)

    store = relationship("Store", back_populates="event_logs")
```

- [ ] **Step 5: Write `backend/models/alert.py`**

```python
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alerts_store_created", "store_id", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    alert_type = Column(String(64), nullable=False)
    severity = Column(String(16), default="warning", index=True)
    message = Column(Text)
    extra_data = Column(JSON, default=dict)
    acknowledged = Column(Integer, default=0, index=True)
    created_at = Column(DateTime, default=datetime.now(UTC), index=True)

    store = relationship("Store", back_populates="alerts")
```

- [ ] **Step 6: Write `backend/models/report.py`**

```python
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (Index("ix_reports_store_created", "store_id", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    report_type = Column(String(32), nullable=False, index=True)
    content_md = Column(Text, nullable=True)
    content_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.now(UTC), index=True)

    store = relationship("Store", back_populates="reports")
```

- [ ] **Step 7: Run tests**

Run: `cd backend && uv run pytest ../tests/ -v`
Expected: 16/16 PASS

- [ ] **Step 8: Run lint**

Run: `cd backend && uv run ruff check models/`
Expected: no errors

- [ ] **Step 9: Commit**

```bash
git add backend/models/store.py backend/models/workflow.py backend/models/agent_run.py backend/models/event_log.py backend/models/alert.py backend/models/report.py
git commit -m "refactor(models): split into one file per model

- models/store.py, workflow.py, agent_run.py, event_log.py, alert.py, report.py
- Removed extend_existing from __table_args__ (handled by migrations)
- models/__init__.py re-exports all models and enums"
```

---

## Task 4: Split schemas into individual files

**Files:**
- Create: `backend/schemas/__init__.py`
- Create: `backend/schemas/store.py`
- Create: `backend/schemas/workflow.py`
- Create: `backend/schemas/agent.py`
- Create: `backend/schemas/timeline.py`
- Create: `backend/schemas/dashboard.py`
- Create: `backend/schemas/alert.py`
- Read: `backend/schemas.py` (current file — split by section comments)

- [ ] **Step 1: Write `backend/schemas/store.py`**

```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class StoreImportItem(BaseModel):
    store_id: str
    name: str
    city: str | None = None
    category: str | None = None
    rating: float = 0.0
    monthly_orders: int = 0
    gmv_last_7d: float = 0.0
    review_count: int = 0
    review_reply_rate: float = 0.0
    ros_health: str = "unknown"
    competitor_avg_discount: float = 0.0
    issues: list[str] = Field(default_factory=list)
    raw_data: dict = Field(default_factory=dict)


class StoreImportRequest(BaseModel):
    stores: list[StoreImportItem]


class StoreResponse(BaseModel):
    id: int
    store_id: str
    name: str
    city: str | None
    category: str | None
    rating: float
    monthly_orders: int
    gmv_last_7d: float
    review_count: int
    review_reply_rate: float
    ros_health: str
    competitor_avg_discount: float
    issues: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Write `backend/schemas/workflow.py`**

```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class WorkflowStatusResponse(BaseModel):
    store_id: int
    store_name: str
    current_state: str
    consecutive_failures: int
    retry_count: int
    started_at: datetime | None
    recent_agent_runs: list["AgentRunResponse"]

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Write `backend/schemas/agent.py`**

```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AgentRunResponse(BaseModel):
    id: int
    agent_type: str
    status: str
    state_at_run: str | None
    output_data: dict
    error_msg: str | None
    retry_count: int
    duration_ms: int
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Write `backend/schemas/timeline.py`**

```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EventLogResponse(BaseModel):
    id: int
    event_type: str
    from_state: str | None
    to_state: str | None
    agent_type: str | None
    message: str | None
    extra_data: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TimelineResponse(BaseModel):
    store_id: int
    store_name: str
    current_state: str
    events: list[EventLogResponse]
```

- [ ] **Step 5: Write `backend/schemas/dashboard.py`**

```python
from __future__ import annotations

from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    total_stores: int
    state_distribution: dict[str, int]
    anomaly_count: int
    manual_review_queue: list[dict]
    recent_alerts: list[dict]
    recent_agent_runs: list[dict]
```

- [ ] **Step 6: Write `backend/schemas/alert.py`**

```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AlertResponse(BaseModel):
    id: int
    store_id: int
    alert_type: str
    severity: str
    message: str | None
    acknowledged: bool
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 7: Write `backend/schemas/__init__.py`**

```python
from __future__ import annotations

from .agent import AgentRunResponse
from .alert import AlertResponse
from .dashboard import DashboardSummaryResponse
from .store import StoreImportItem, StoreImportRequest, StoreResponse
from .timeline import EventLogResponse, TimelineResponse
from .workflow import WorkflowStatusResponse

__all__ = [
    "AgentRunResponse",
    "AlertResponse",
    "DashboardSummaryResponse",
    "EventLogResponse",
    "StoreImportItem",
    "StoreImportRequest",
    "StoreResponse",
    "TimelineResponse",
    "WorkflowStatusResponse",
]
```

- [ ] **Step 8: Update `WorkflowStatusResponse` forward reference**

Add to `backend/schemas/workflow.py`, after the `AgentRunResponse` import:
```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from backend.schemas.agent import AgentRunResponse


class WorkflowStatusResponse(BaseModel):
    ...
    recent_agent_runs: list[AgentRunResponse]  # no quotes needed
```

- [ ] **Step 9: Run tests**

Run: `cd backend && uv run pytest ../tests/ -v`
Expected: 16/16 PASS

- [ ] **Step 10: Run lint**

Run: `cd backend && uv run ruff check schemas/`
Expected: no errors

- [ ] **Step 11: Commit**

```bash
git add backend/schemas/
git commit -m "refactor(schemas): split into one file per schema group

- schemas/store.py, workflow.py, agent.py, timeline.py, dashboard.py, alert.py
- schemas/__init__.py unified exports
- model_config replaces deprecated Config class"
```

---

## Task 5: Update all imports across the codebase

**Files:**
- Modify: `backend/main.py` — update schema and model imports
- Modify: `backend/orchestrator/engine.py` — update model imports
- Modify: `backend/agents/base.py` — update AgentStatus import
- Modify: `tests/conftest.py` — update model imports
- Modify: `tests/test_example.py` — update model imports

- [ ] **Step 1: Update `backend/main.py` imports**

Replace:
```python
from backend.database import AsyncSessionLocal, get_db, async_engine
from backend.models import (
    Store, WorkflowInstance, AgentRun, EventLog, Alert, Report, WorkflowState,
)
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
```

With:
```python
from backend.database import AsyncSessionLocal, get_db, async_engine
from backend.models import Alert, EventLog, Store, WorkflowInstance, WorkflowState
from backend.schemas import (
    AgentRunResponse,
    DashboardSummaryResponse,
    EventLogResponse,
    StoreImportItem,
    StoreImportRequest,
    StoreResponse,
    TimelineResponse,
    WorkflowStatusResponse,
)
```

- [ ] **Step 2: Update `backend/orchestrator/engine.py` imports**

Replace the current `from backend.models import (...)` block with:
```python
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
```

Also update the `AgentStatus` import:
```python
from backend.models import AgentStatus as AgentResultStatus
```

- [ ] **Step 3: Update `backend/agents/base.py`**

Remove the `AgentStatus` class definition (it now lives in `models._enums`). Add import at top:
```python
from backend.models import AgentStatus
```

The `AgentStatus` enum definition should be **deleted** from `base.py`. The dataclass `AgentResult` still uses `AgentStatus` — it just imports from the new location.

- [ ] **Step 4: Update `tests/conftest.py`**

Replace:
```python
from backend.database import Base
```
With (no change needed — `Base` is still in `database.py` as a re-export):

```python
from backend.database import Base
```

Replace the individual model imports:
```python
from backend.models import (
    Store, WorkflowInstance, AgentRun, EventLog, Alert, Report,
    WorkflowState, VALID_TRANSITIONS,
)
```

- [ ] **Step 5: Update `tests/test_example.py`**

Update the `from backend.models import (...)` import to include all models and remove `AgentStatus` (now from `backend.models`):
```python
from backend.models import (
    Store, WorkflowInstance, AgentRun, EventLog, Alert, Report,
    WorkflowState, VALID_TRANSITIONS, AgentStatus,
)
```

Update `AgentStatus` in test imports from `backend.agents.base`:
```python
from backend.agents.base import BaseAgent, AgentResult
from backend.agents.analyzer import AnalyzerAgent
from backend.agents.reporter import ReporterAgent
```

- [ ] **Step 6: Run tests**

Run: `cd backend && uv run pytest ../tests/ -v`
Expected: 16/16 PASS

- [ ] **Step 7: Run lint**

Run: `cd backend && uv run ruff check .`
Expected: All checks passed

- [ ] **Step 8: Commit**

```bash
git add backend/main.py backend/orchestrator/engine.py backend/agents/base.py tests/conftest.py tests/test_example.py
git commit -m "refactor: update all imports to new model/schema paths

- main.py, engine.py, agents/base.py, tests/ — updated imports
- Removed duplicate AgentStatus enum from agents/base.py
- models and schemas now imported from backend.models and backend.schemas"
```

---

## Task 6: Delete old monolithic files

**Files:**
- Delete: `backend/models.py` (replaced by `backend/models/`)
- Delete: `backend/schemas.py` (replaced by `backend/schemas/`)

- [ ] **Step 1: Delete old files**

Run:
```bash
rm backend/models.py backend/schemas.py
```

- [ ] **Step 2: Verify no broken imports**

Run: `cd backend && uv run python -c "from backend.models import *; from backend.schemas import *; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Run full test suite**

Run: `cd backend && uv run pytest ../tests/ -v`
Expected: 16/16 PASS

- [ ] **Step 4: Run full lint**

Run: `cd backend && uv run ruff check .`
Expected: All checks passed

- [ ] **Step 5: Format all**

Run: `cd backend && uv run ruff format .`

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: remove legacy models.py and schemas.py

- Replaced by backend/models/ and backend/schemas/ modules
- All imports updated across the codebase"
```

---

## Verification

1. `cd backend && uv run python -c "from backend.models import *; from backend.schemas import *"` — OK
2. `cd backend && uv run python -c "from backend.database import async_engine, get_db"` — OK
3. `make backend-test` — 16/16 PASS
4. `make backend-lint` — All checks passed
5. `make backend-fmt` — formatted
6. `make backend-dev` — starts without import errors
7. `ls backend/models/` — shows `__init__.py`, `_enums.py`, `store.py`, `workflow.py`, `agent_run.py`, `event_log.py`, `alert.py`, `report.py`
8. `ls backend/schemas/` — shows `__init__.py`, `store.py`, `workflow.py`, `agent.py`, `timeline.py`, `dashboard.py`, `alert.py`
