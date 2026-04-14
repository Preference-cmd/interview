# SQL Migration System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `Base.metadata.create_all()` with a real SQL migration system that tracks applied migrations and supports schema evolution on existing databases.

**Architecture:** A lightweight migration runner (no Alembic dependency) that reads SQL files from `migrations/sql/` and tracks applied versions in a `schema_migrations` table. Executed automatically on app startup via FastAPI lifespan.

**Tech Stack:** SQLAlchemy async engine, aiosqlite, raw SQL files

---

## File Map

```
backend/
├── migrations/
│   ├── __init__.py
│   ├── runner.py              ← MigrationRunner class
│   └── sql/
│       └── 0001_initial_schema.sql  ← all CREATE TABLE / INDEX statements
├── main.py                    ← lifespan calls runner.run_pending()
└── Makefile                   ← add backend-migrate
```

---

## Task 1: Create migration SQL file

**Files:**
- Create: `backend/migrations/sql/0001_initial_schema.sql`
- Read: `backend/models.py` (current table definitions)

- [ ] **Step 1: Write the migration SQL file**

Create `backend/migrations/sql/0001_initial_schema.sql` with the following content:

```sql
-- Schema migrations tracking table
CREATE TABLE IF NOT EXISTS schema_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL UNIQUE,
    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Initial migration record
INSERT OR IGNORE INTO schema_migrations (version) VALUES ('0001_initial_schema');

-- Stores
CREATE TABLE IF NOT EXISTS stores (
    id INTEGER NOT NULL,
    store_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    city TEXT,
    category TEXT,
    rating REAL DEFAULT 0.0,
    monthly_orders INTEGER DEFAULT 0,
    gmv_last_7d REAL DEFAULT 0.0,
    review_count INTEGER DEFAULT 0,
    review_reply_rate REAL DEFAULT 0.0,
    ros_health TEXT DEFAULT 'unknown',
    competitor_avg_discount REAL DEFAULT 0.0,
    issues TEXT DEFAULT '[]',
    raw_data TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_stores_store_id ON stores (store_id);

-- Workflow instances (one per store, unique constraint enforced)
CREATE TABLE IF NOT EXISTS workflow_instances (
    id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    current_state TEXT DEFAULT 'NEW_STORE',
    consecutive_failures INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    started_at DATETIME,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (store_id) REFERENCES stores (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_workflow_store_id ON workflow_instances (store_id);
CREATE INDEX IF NOT EXISTS ix_workflow_instances_current_state ON workflow_instances (current_state);

-- Agent runs
CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    agent_type TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    state_at_run TEXT,
    input_data TEXT DEFAULT '{}',
    output_data TEXT DEFAULT '{}',
    error_msg TEXT,
    retry_count INTEGER DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (store_id) REFERENCES stores (id)
);

CREATE INDEX IF NOT EXISTS ix_agent_runs_store_id ON agent_runs (store_id);
CREATE INDEX IF NOT EXISTS ix_agent_runs_status ON agent_runs (status);
CREATE INDEX IF NOT EXISTS ix_agent_runs_created_at ON agent_runs (created_at);
CREATE INDEX IF NOT EXISTS ix_agent_runs_store_created ON agent_runs (store_id, created_at);

-- Event logs
CREATE TABLE IF NOT EXISTS event_logs (
    id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    from_state TEXT,
    to_state TEXT,
    agent_type TEXT,
    message TEXT,
    extra_data TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (store_id) REFERENCES stores (id)
);

CREATE INDEX IF NOT EXISTS ix_event_logs_store_id ON event_logs (store_id);
CREATE INDEX IF NOT EXISTS ix_event_logs_event_type ON event_logs (event_type);
CREATE INDEX IF NOT EXISTS ix_event_logs_created_at ON event_logs (created_at);
CREATE INDEX IF NOT EXISTS ix_event_logs_store_created ON event_logs (store_id, created_at);

-- Alerts
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    alert_type TEXT NOT NULL,
    severity TEXT DEFAULT 'warning',
    message TEXT,
    extra_data TEXT DEFAULT '{}',
    acknowledged INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (store_id) REFERENCES stores (id)
);

CREATE INDEX IF NOT EXISTS ix_alerts_store_id ON alerts (store_id);
CREATE INDEX IF NOT EXISTS ix_alerts_severity ON alerts (severity);
CREATE INDEX IF NOT EXISTS ix_alerts_acknowledged ON alerts (acknowledged);
CREATE INDEX IF NOT EXISTS ix_alerts_created_at ON alerts (created_at);
CREATE INDEX IF NOT EXISTS ix_alerts_store_created ON alerts (store_id, created_at);

-- Reports
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    report_type TEXT NOT NULL,
    content_md TEXT,
    content_json TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (store_id) REFERENCES stores (id)
);

CREATE INDEX IF NOT EXISTS ix_reports_store_id ON reports (store_id);
CREATE INDEX IF NOT EXISTS ix_reports_report_type ON reports (report_type);
CREATE INDEX IF NOT EXISTS ix_reports_created_at ON reports (created_at);
CREATE INDEX IF NOT EXISTS ix_reports_store_created ON reports (store_id, created_at);
```

**Note:** SQLite does not support `DEFAULT CURRENT_TIMESTAMP` for `DATETIME` in a reliable cross-platform way, but aiosqlite + SQLAlchemy handle this fine. All JSON columns use `TEXT` because SQLite stores JSON as TEXT natively.

- [ ] **Step 2: Verify SQL syntax**

Run: `sqlite3 :memory: < backend/migrations/sql/0001_initial_schema.sql`
Expected: no output (success, silent)

---

## Task 2: Create MigrationRunner class

**Files:**
- Create: `backend/migrations/__init__.py`
- Create: `backend/migrations/runner.py`
- Read: `backend/database.py` (current engine definition)

- [ ] **Step 1: Write `backend/migrations/__init__.py`**

```python
from .runner import MigrationRunner

__all__ = ["MigrationRunner"]
```

- [ ] **Step 2: Write `backend/migrations/runner.py`**

```python
from __future__ import annotations

import re
from pathlib import Path
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///./multi_agent_ops.db"


class MigrationRunner:
    """
    Lightweight SQL migration runner.
    Reads SQL files from migrations/sql/, applies pending ones,
    and records them in the schema_migrations table.
    """

    def __init__(self, engine: AsyncEngine):
        self.engine = engine

    async def run_pending(self) -> list[str]:
        """Run all pending migrations. Returns list of applied versions."""
        applied: set[str] = set()
        async for conn in self._connect():
            applied = await self._get_applied(conn)

        applied_list = list(applied)
        migrations_dir = Path(__file__).parent / "sql"
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            version = _extract_version(sql_file.name)
            if version not in applied:
                async for conn in self._connect():
                    await self._apply(conn, sql_file, version)
                    applied_list.append(version)
        return applied_list

    def _connect(self) -> AsyncIterator[AsyncSession]:
        session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        session = session_factory()
        try:
            yield session
        finally:
            pass

    async def _get_applied(self, conn: AsyncSession) -> set[str]:
        result = await conn.execute(text("SELECT version FROM schema_migrations"))
        rows = result.fetchall()
        return {row[0] for row in rows}

    async def _apply(self, conn: AsyncSession, sql_file: Path, version: str) -> None:
        sql_content = sql_file.read_text()
        for statement in sql_content.split(";"):
            statement = statement.strip()
            if statement:
                await conn.execute(text(statement))
        await conn.execute(
            text("INSERT OR IGNORE INTO schema_migrations (version) VALUES (:version)"),
            {"version": version},
        )
        await conn.commit()


def _extract_version(filename: str) -> str:
    """Extract version from '0001_initial_schema.sql' -> '0001_initial_schema'."""
    return filename.replace(".sql", "")
```

**Note:** Uses raw `text()` SQL because SQLite `aiosqlite` requires running DDL statements separately.

- [ ] **Step 3: Run lint on new files**

Run: `cd backend && uv run ruff check migrations/`
Expected: no errors

- [ ] **Step 4: Format new files**

Run: `cd backend && uv run ruff format migrations/`
Expected: files formatted

- [ ] **Step 5: Commit**

Run:
```bash
cd /Users/pref2rence/project/lls/multi-agent-ops
git add backend/migrations/
git commit -m "feat(db): add SQL migration system

- migrations/sql/0001_initial_schema.sql — all tables, indexes, constraints
- migrations/runner.py — MigrationRunner with pending-migration detection
- schema_migrations table tracks applied versions"
```

---

## Task 3: Wire into FastAPI lifespan

**Files:**
- Modify: `backend/main.py:1-35` (lifespan function)
- Read: `backend/migrations/runner.py` (already created in Task 2)
- Read: `backend/database.py` (for current engine import)

- [ ] **Step 1: Add migration import and runner call to lifespan**

Replace the current `lifespan` function in `backend/main.py` (lines 29-35):

Old code:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down...")
```

New code:
```python
from backend.migrations import MigrationRunner

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Running pending migrations...")
    from backend.database import async_engine
    runner = MigrationRunner(async_engine)
    applied = await runner.run_pending()
    if applied:
        logger.info(f"Migrations applied: {applied}")
    else:
        logger.info("No pending migrations")
    yield
    logger.info("Shutting down...")
```

- [ ] **Step 2: Add import for `async_engine`**

Find in `backend/main.py` the line `from backend.database import AsyncSessionLocal, get_db, init_db` and update it to:
```python
from backend.database import AsyncSessionLocal, get_db, async_engine
```

- [ ] **Step 3: Remove `init_db` import (no longer needed)**

Remove `init_db` from the import line.

- [ ] **Step 4: Run tests to verify no breakage**

Run: `cd backend && uv run pytest ../tests/ -v`
Expected: 16/16 PASS

- [ ] **Step 5: Run lint**

Run: `cd backend && uv run ruff check .`
Expected: All checks passed

- [ ] **Step 6: Commit**

Run:
```bash
git add backend/main.py
git commit -m "feat(db): wire MigrationRunner into FastAPI lifespan"
```

---

## Task 4: Add Makefile target

**Files:**
- Modify: `Makefile:2` (phony declaration)
- Modify: `Makefile:14` (help text)
- Modify: `Makefile:43` (new target)

- [ ] **Step 1: Add `backend-migrate` to phony and help**

In `Makefile`, add `backend-migrate` to the phony line:
```
.PHONY: ... backend-migrate
```

Add to the Backend help section (after `make backend-clean`):
```
	@echo "  make backend-migrate    Run pending database migrations"
```

Add the target after `backend-clean:`:
```make
backend-migrate:
	cd backend && uv run python -m migrations.runner
```

- [ ] **Step 2: Commit**

Run:
```bash
git add Makefile
git commit -m "chore: add backend-migrate Make target"
```

---

## Verification

1. `make backend-migrate` — apply pending migrations (creates DB file with all tables)
2. `make backend-test` — 16/16 PASS
3. `make backend-lint` — All checks passed
4. `ls backend/*.db` — `multi_agent_ops.db` created
5. `sqlite3 backend/multi_agent_ops.db ".schema schema_migrations"` — shows table definition
6. Run migrate twice — second run says "No pending migrations"
