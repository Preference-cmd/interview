# Auto State Transition Plan

> Date: 2026-04-14
> Status: Implementation Plan
> Phase: auto-state-transition

## Context

The current `POST /stores/{id}/start` handles exactly one workflow state per call. The goal is to make it run through all states automatically with configurable delays between transitions, using `asyncio.create_task()` for background execution per the 2026-04-14 decision record.

This is a **Level 1** change (modifying existing patterns, using known `asyncio` primitives). No external discovery needed.

---

## Architecture Decision

### Approach: Lifespan-scoped `asyncio.Task` registry

- One background task per store, stored in FastAPI app state
- Each task owns its own `AsyncSession` for all DB operations (stateless engine pattern)
- No Celery, no Redis — SQLite + asyncio is sufficient
- State is persisted after each step, so restarts lose only in-flight tasks (user re-calls `/start` to resume)

### Why not process/thread?
- `asyncio.create_task()` is already in the decision record
- Tasks share memory with the main event loop — no serialization overhead
- FastAPI + uvicorn runs single-threaded by default; asyncio tasks fit naturally
- Process workers would require Redis for shared state; threads add unnecessary complexity

### Why not Celery/Redis?
- Overkill for 5-state sequential workflow with mock agents
- Adds deployment complexity (worker processes, broker)
- The mock agents complete in milliseconds — no need for distributed task queue

### Task lifecycle

```
HTTP request (/start)
  -> create asyncio.create_task(run_workflow_loop(store_id, delay_seconds))
  -> task stored in app.state._workflow_tasks[store_id]
  -> HTTP response returns immediately

Background task:
  while True:
    run one state (same as current run_workflow logic)
    persist state to DB
    if terminal state (DONE/MANUAL_REVIEW): break
    await asyncio.sleep(delay_seconds)
    if cancelled (new /start or stop): break
```

### Terminal states
- `DONE` — workflow completed successfully
- `MANUAL_REVIEW` — too many consecutive failures
- Task cancelled — new `/start` for same store, or server shutdown

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/orchestrator/engine.py` | Add `run_workflow_loop(store_id, delay_seconds)` method |
| `backend/service/workflow.py` | Change `start_workflow` to spawn background task |
| `backend/main.py` | Add lifespan cleanup for running tasks; expose task registry |
| `backend/routes/workflows.py` | Add `POST /stores/{id}/stop` endpoint |
| `backend/schemas/workflow.py` | Add `WorkflowLoopConfig` schema |
| `backend/models/workflow.py` | Add `is_running` field to `WorkflowInstance` |
| `doc/STATE.md` | Update decision record and P1 items |

### Files to Create

| File | Purpose |
|------|---------|
| `backend/migrations/sql/0002_add_workflow_fields.sql` | Add `is_running` column |
| `tests/test_auto_transition.py` | Integration tests for the loop |

---

## Step-by-Step Implementation

### Phase 1: Data model + schema (foundation)

**1a. Add `is_running` field to `WorkflowInstance`**

`backend/models/workflow.py`:
```python
is_running = Column(Boolean, default=False, index=True)
```

`backend/migrations/sql/0002_add_workflow_fields.sql`:
```sql
ALTER TABLE workflow_instances ADD COLUMN is_running INTEGER DEFAULT 0 NOT NULL;
CREATE INDEX IF NOT EXISTS ix_workflow_instances_is_running ON workflow_instances(is_running);
```

**1b. Add request schema**

`backend/schemas/workflow.py` — add:
```python
class WorkflowStartRequest(BaseModel):
    delay_seconds: float = 3.0  # default 3s between states
    force_restart: bool = False  # cancel any running loop and restart
```

**1c. Update response schema**

Add `is_running: bool` to `WorkflowStatusResponse`.

---

### Phase 2: Background loop in engine

**2a. Add `run_workflow_loop` to `WorkflowEngine`**

```python
async def run_workflow_loop(
    self,
    store: Store,
    delay_seconds: float = 3.0,
) -> WorkflowInstance:
    """
    Run workflow continuously through all states.
    Creates its own AsyncSession so it survives across HTTP requests.
    """
    from backend.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        # Re-create stores with new session
        wf_store = WorkflowStore(session)
        ar_store = AgentRunStore(session)
        rp_store = ReportStore(session)
        emitter = EventEmitter(session)

        # Re-fetch workflow with this session
        wf = await wf_store.get_or_create_workflow(store.id)

        while True:
            state = WorkflowState(wf.current_state)

            if state in (WorkflowState.DONE, WorkflowState.MANUAL_REVIEW):
                break

            # Run one step (same logic as run_workflow)
            # ... (copy agent execution + failure handling + transition logic)

            await session.commit()  # Persist after each step

            # Check if terminal state reached
            next_state = WorkflowState(wf.current_state)
            if next_state in (WorkflowState.DONE, WorkflowState.MANUAL_REVIEW):
                break

            await asyncio.sleep(delay_seconds)

    return wf
```

**Key design decisions:**
- Each loop iteration commits after all DB changes (SQLite handles this well)
- Creates fresh session per iteration to avoid stale object state
- The outer `async with AsyncSessionLocal() as session` spans the whole loop so one workflow has consistent DB context per iteration
- Commits inside the loop after each state transition

**2b. Refactor `run_workflow` to avoid duplication**

Extract the "run one state" logic into a private method:

```python
async def _run_single_state(
    self,
    store: Store,
    wf: WorkflowInstance,
    session: AsyncSession,
    state: WorkflowState,
) -> WorkflowState:
    """
    Run all agents for the given state, handle failures,
    return the next state.
    """
    # ... current run_workflow logic (agent loop, failure handling, transition)
```

Then `run_workflow` and `run_workflow_loop` both call `_run_single_state`.

---

### Phase 3: Task registry + service changes

**3a. Add task registry to app state**

`backend/main.py` — in `lifespan()`:
```python
workflow_tasks: dict[int, asyncio.Task] = {}
app.state._workflow_tasks = workflow_tasks

# On shutdown:
for task in workflow_tasks.values():
    task.cancel()
await asyncio.gather(*workflow_tasks.values(), return_exceptions=True)
```

**3b. Modify `WorkflowService.start_workflow`**

```python
async def start_workflow(
    self,
    store_id: int,
    delay_seconds: float = 3.0,
    force_restart: bool = False,
) -> dict[str, int | str | bool]:
    from backend.database import AsyncSessionLocal

    store = await self._require_store(store_id)
    wf = await self._workflow.get_or_create_workflow(store.id)

    if wf.current_state in (WorkflowState.DONE.value, WorkflowState.MANUAL_REVIEW.value):
        return {"message": "Workflow already terminal", "store_id": store_id, "is_running": False}

    # Cancel existing task if force_restart
    if force_restart and store.id in app.state._workflow_tasks:
        app.state._workflow_tasks[store.id].cancel()
        del app.state._workflow_tasks[store.id]

    # Check if already running
    if store.id in app.state._workflow_tasks:
        task = app.state._workflow_tasks[store.id]
        if not task.done():
            return {"message": "Workflow already running", "store_id": store_id, "is_running": True}

    # Spawn background task
    loop = asyncio.get_running_loop()
    task = loop.create_task(
        self._run_loop_background(store, delay_seconds)
    )
    app.state._workflow_tasks[store.id] = task

    return {"message": "Workflow started", "store_id": store_id, "is_running": True}
```

**3c. Add stop endpoint**

`backend/routes/workflows.py`:
```python
@router.post("/{store_id}/stop")
async def stop_workflow(store_id: int, db: AsyncSession = Depends(get_db)) -> dict[str, int | str | bool]:
    task = app.state._workflow_tasks.get(store_id)
    if task and not task.done():
        task.cancel()
        del app.state._workflow_tasks[store_id]
        return {"message": "Workflow stopped", "store_id": store_id, "is_running": False}
    return {"message": "No running workflow", "store_id": store_id, "is_running": False}
```

---

### Phase 4: Tests

**4a. `tests/test_auto_transition.py`**

Key test cases:
1. `test_loop_runs_all_states` — verify it transitions through all 5 states
2. `test_loop_respects_delay` — verify `asyncio.sleep` is called with correct duration
3. `test_loop_stops_at_done` — verify it exits when state is DONE
4. `test_loop_escalates_on_max_failures` — verify MANUAL_REVIEW after 3 failures
5. `test_concurrent_start_is_noop` — calling `/start` while running returns existing task
6. `test_force_restart_cancels_existing` — `force_restart=True` cancels old task
7. `test_loop_persists_state_after_each_step` — verify DB has correct state after each iteration
8. `test_loop_creates_agent_runs_for_each_state` — verify AgentRun records created

---

## State Persistence Concerns

| Scenario | Behavior |
|----------|----------|
| Server restart mid-loop | Task lost. DB has last persisted state. User calls `/start` again to resume. Safe — no data loss. |
| SQLite write failure | Exception propagates, task dies, state unchanged. User sees error via `/status`. |
| Concurrent `/start` for same store | Second call sees `task.done() == False`, returns "already running". Use `force_restart=True` to override. |
| Task cancellation (stop or restart) | Task cancelled mid-step. DB has partial state from last commit. Safe — no inconsistency. |

### No persistence gap
Each loop iteration calls `session.commit()` after the state transition, so at most one state step is uncommitted if the server crashes.

---

## Error Handling and Recovery

| Error | Behavior |
|-------|---------|
| Agent failure < 3 times | Retry within same state, then retry on next loop iteration |
| Agent failure 3 times | Escalate to MANUAL_REVIEW, loop exits |
| DB commit failure | Task raises, loop exits. Last committed state remains. |
| `asyncio.CancelledError` | Clean exit, no state change |
| Store not found | HTTP 404 from service layer before task spawns |

---

## Concerns to Flag

### 1. Memory leak if tasks are not cleaned up
**Risk:** If a store completes but the task reference is never removed from `app.state._workflow_tasks`, it accumulates over time.

**Mitigation:** Remove the task reference from the dict in both success and cancellation paths:
```python
# After loop exits in background task:
if store.id in app.state._workflow_tasks:
    del app.state._workflow_tasks[store.id]
```

### 2. SQLite write contention with long-running tasks
**Risk:** If many stores run loops simultaneously, SQLite write locks could cause `database is locked` errors.

**Mitigation:** For mock agents completing in milliseconds, this is unlikely. Add retry logic on `OperationalError` with `database is locked` message (SQLite busy timeout already set). If it becomes a problem, consider per-store locking or moving to PostgreSQL.

### 3. The `run_workflow_loop` refactor duplicates `run_workflow` logic
**Risk:** Two code paths for the same core logic.

**Mitigation:** Extract to `_run_single_state()` as described in 2b. Both `run_workflow` and `run_workflow_loop` call this method. This is the primary refactoring goal.

### 4. No visibility into loop progress mid-execution
**Risk:** User calls `/start`, gets "Workflow started", but no way to know which state it's in without polling `/status`.

**Mitigation:** `/status` already returns `current_state` and `recent_agent_runs`. For now, this is sufficient. A WebSocket or SSE endpoint could be added later but is out of scope.

### 5. `force_restart` behavior during a running step
**Risk:** If `force_restart=True` is called while the loop is mid-state (running agents), the cancellation happens at the next `await` point (the `asyncio.sleep` or a DB call). The in-flight state step completes before cancellation takes effect.

**Mitigation:** Document this behavior. It's acceptable — interrupting an in-flight DB transaction would be worse.

---

## Verification

```bash
cd backend && make backend-test   # All existing tests pass
cd backend && python -m pytest tests/test_auto_transition.py -v  # New tests pass
make backend-lint                  # ruff passes
```

Manual verification:
```bash
# Start workflow — should auto-run through all states
curl -X POST http://localhost:8000/stores/1/start \
  -H "Content-Type: application/json" \
  -d '{"delay_seconds": 2.0}'

# Check status repeatedly
curl http://localhost:8000/stores/1/status | jq '.current_state'

# Stop mid-execution
curl -X POST http://localhost:8000/stores/1/stop
```

Expected: state transitions from `NEW_STORE` -> `DIAGNOSIS` -> `FOUNDATION` -> `DAILY_OPS` -> `WEEKLY_REPORT` -> `DONE` over ~10 seconds (5 states x 2s delay).

---

## Implementation Order

1. **Plan 01:** Data model (`is_running` field + migration) + schemas
2. **Plan 02:** Engine refactor — extract `_run_single_state`, add `run_workflow_loop`
3. **Plan 03:** Service + route changes — task registry, stop endpoint, lifespan cleanup
4. **Plan 04:** Tests for auto-transition behavior
