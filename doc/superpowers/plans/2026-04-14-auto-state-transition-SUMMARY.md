# Phase auto-state-transition Plan 2026-04-14: Auto State Transition Summary

**Phase:** auto-state-transition
**Plan:** 2026-04-14-auto-state-transition
**Status:** Complete
**Completed:** 2026-04-14

## Objective

Modify `POST /stores/{id}/start` to run a background loop that executes all workflow states automatically with configurable delays between transitions, using `asyncio.create_task()`.

## One-liner

Background workflow auto-transition via lifespan-scoped `asyncio.Task` registry with per-iteration DB persistence.

## Commits

| Hash | Type | Message |
|------|------|---------|
| `9e7a158` | feat | add is_running field and WorkflowStartRequest schema |
| `57804cc` | feat | extract _run_single_state and add run_workflow_loop |
| `39ab32d` | feat | wire task registry, loop spawning, and stop endpoint |
| `a1e37f0` | test | add 11 test cases for background loop behavior |

## Files Created

- `backend/migrations/sql/0002_add_workflow_fields.sql` — adds `is_running` column to workflow_instances
- `tests/test_auto_transition.py` — 11 test cases for loop, cancellation, and service behavior

## Files Modified

- `backend/models/workflow.py` — added `is_running` Boolean field (default=False, indexed)
- `backend/schemas/workflow.py` — added `WorkflowStartRequest` (delay_seconds, force_restart) and `is_running` to `WorkflowStatusResponse`
- `backend/schemas/__init__.py` — export `WorkflowStartRequest`
- `backend/orchestrator/engine.py` — extracted `_run_single_state()`, kept `run_workflow()` for backward compatibility, added `run_workflow_loop(store_id, delay_seconds)` with session-owned stores and graceful cancellation
- `backend/service/workflow.py` — added `start_workflow_loop()` (spawns background task), `stop_workflow()` (cancels task), updated `get_status()` to return `is_running`
- `backend/routes/workflows.py` — `/start` now accepts optional `WorkflowStartRequest` body, added `/stop` endpoint, both use task registry from `app.state`
- `backend/main.py` — lifespan startup creates `_workflow_tasks` dict, shutdown cancels all running tasks

## Key Design Decisions

1. **Session-owned engine in loop**: `run_workflow_loop` creates stores bound to its own `AsyncSession` inside the loop, ensuring DB consistency across iterations. An inner `WorkflowEngine` built by `_build_loop_engine()` handles state execution.

2. **Graceful cancellation**: `CancelledError` from `_run_single_state` or `asyncio.sleep` is caught inside the loop (not propagated through `async with`), `is_running` is set to False, and the function returns cleanly. An outer `try/except CancelledError` handles server shutdown (propagates).

3. **Terminal state check on start**: Both service methods check if `current_state` is `DONE` or `MANUAL_REVIEW` before spawning or returning.

4. **`is_running` field**: Persisted to DB via `wf.is_running = True/False` with `session.add()` + `session.commit()` on each iteration boundary. Read by `get_status()` from the workflow record.

## Architecture

```
HTTP /start request
  -> WorkflowService.start_workflow_loop()
    -> asyncio.create_task(_run_loop_background(store_id, delay_seconds))
    -> task stored in app.state._workflow_tasks[store_id]
    -> HTTP 200 returned immediately

Background task (owns AsyncSession):
  while True:
    wf.is_running = True; session.commit()
    run one state (_run_single_state)
    wf.is_running = False; session.commit()
    if terminal: break
    await asyncio.sleep(delay_seconds)
    except CancelledError: return wf  # clean exit
```

## Deviations from Plan

None — plan executed as written.

## Test Coverage

57 total tests (46 existing + 11 new):

| Test | Coverage |
|------|----------|
| `test_loop_transitions_through_all_states` | 5 state transitions, 4 sleeps between states |
| `test_loop_stops_at_done` | Exits immediately when already DONE |
| `test_loop_stops_at_manual_review` | Exits immediately when already MANUAL_REVIEW |
| `test_loop_calls_run_single_state_per_iteration` | 5 iterations for 5 states |
| `test_loop_cancellation_clears_running_flag` | CancelledError sets is_running=False, returns wf |
| `test_start_workflow_loop_checks_done_terminal` | Returns "already terminal" for DONE |
| `test_start_workflow_loop_checks_manual_review_terminal` | Returns "already terminal" for MANUAL_REVIEW |
| `test_stop_workflow_cancels_and_removes_task` | Cancels and removes from registry |
| `test_stop_workflow_no_running_task` | Returns "No running workflow" |
| `test_concurrent_start_is_noop` | Second start returns "already running" |
| `test_force_restart_cancels_existing_and_spawns_new` | Cancels old, registers new task |

## Metrics

- **Duration:** ~10 minutes
- **Tasks completed:** 4 (Phase 1-4)
- **Files created:** 2
- **Files modified:** 6
- **Tests added:** 11
- **Total tests:** 57 (all passing)
- **Lint:** All checks passed
- **Format:** All checks passed

## Self-Check

- [x] All 57 tests pass
- [x] ruff lint passes
- [x] ruff format passes
- [x] All plan files exist (plan, commits)
- [x] Migration SQL file created
- [x] `is_running` field added to model
- [x] `WorkflowStartRequest` schema created
- [x] `_run_single_state` extracted
- [x] `run_workflow_loop` added
- [x] Task registry in app.state
- [x] Lifespan shutdown cleanup
- [x] `/stop` endpoint added
- [x] `is_running` in status response
