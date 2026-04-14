# Architecture

## Overview

The system automates the workflow of third-party local-life operations (代运营) agents managing merchant stores on 美团/大众点评 platforms.

```
┌──────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend   │────▶│   FastAPI API   │────▶│  WorkflowEngine │
│  (Next.js)   │◀────│   (main.py)     │◀────│  (orchestrator) │
└──────────────┘     └─────────────────┘     └────────┬────────┘
                                                       │
                         ┌─────────────────────────────┼─────────────────────────────┐
                         ▼                             ▼                             ▼
                  ┌─────────────┐             ┌─────────────────┐           ┌──────────────┐
                  │  Analyzer  │             │    WebOperator   │           │  MobileOp    │
                  │   Agent    │             │    Agent         │           │   Agent      │
                  └─────────────┘             └─────────────────┘           └──────┬───────┘
                                                                                     │
                                                                                     ▼
                                                                            ┌──────────────┐
                                                                            │  Reporter    │
                                                                            │   Agent      │
                                                                            └──────────────┘
                                                                                     │
                                                                                     ▼
                                                                            ┌──────────────┐
                                                                            │  SQLite DB   │
                                                                            │ (6 tables)   │
                                                                            └──────────────┘
```

## State Machine

```
NEW_STORE ──▶ DIAGNOSIS ──▶ FOUNDATION ──▶ DAILY_OPS ──▶ WEEKLY_REPORT ──▶ DONE
                │                │             │              │
                │                │             │              │
                ▼                ▼             ▼              ▼
           MANUAL_REVIEW ◀───────┴─────────────┘              │
                ▲                                        │
                └──────────────────────────────────────────┘
                       (WEEKLY_REPORT can loop back)
```

### State → Agents Mapping

| State | Agents Run |
|-------|-----------|
| `NEW_STORE` | (no agents, just entry point) |
| `DIAGNOSIS` | AnalyzerAgent |
| `FOUNDATION` | WebOperatorAgent |
| `DAILY_OPS` | WebOperatorAgent + MobileOperatorAgent |
| `WEEKLY_REPORT` | ReporterAgent |
| `MANUAL_REVIEW` | (paused, awaiting human intervention) |
| `DONE` | (terminal) |

## Data Model (6 Tables)

```
stores ─────┬── workflow_instances (1:1)
             ├── agent_runs (1:N)
             ├── event_logs (1:N)
             ├── alerts (1:N)
             └── reports (1:N)
```

### stores
Holds merchant store data including KPIs, ROS health, competitor discount, and identified issues.

### workflow_instances
Tracks the current state and retry state for each store's workflow.

### agent_runs
Persisted record of every agent execution: input, output, status, duration, retry count.

### event_logs
Immutable event stream for timeline queries. Events: `workflow_created`, `state_change`, `agent_run`, `report_generated`, `manual_takeover`.

### alerts
Anomalies and manual-intervention signals. Fields: type, severity, acknowledged flag.

### reports
Generated daily/weekly reports. Stores both Markdown and JSON versions.

## Agent Detail

### AnalyzerAgent
- **Input**: store_data, workflow_state
- **Behavior**: Computes health score from rating/review_rate/ROS. Generates issue severity. Outputs recommendations.
- **Failure rate**: 0% (deterministic)
- **Output keys**: `health_score`, `issues`, `recommendations`, `ros_score`

### WebOperatorAgent
- **Input**: store_data, diagnosis (from context)
- **Behavior**: Simulates backend ops (create deal, set discount, sync ROS). Reads issues + diagnosis to take targeted actions.
- **Delay**: 1-3s uniform random
- **Failure rate**: 20%
- **Output keys**: `actions_taken`, `delay_seconds`

### MobileOperatorAgent
- **Input**: store_data
- **Behavior**: Simulates App ops (material check, activity confirm, ROS snapshot).
- **Delay**: 2-5s uniform random
- **Failure rate**: 25%
- **Output keys**: `actions_taken`, `material_status`, `ros_snapshot`

### ReporterAgent
- **Input**: store_data, diagnosis, report_type
- **Behavior**: Generates Markdown report with KPI table and recommendations. Also outputs structured JSON.
- **Failure rate**: 0%
- **Output keys**: `md_report`, `json_report`

## Data Flow

1. **Import**: `POST /stores/import` creates/updates Store rows
2. **Start**: `POST /stores/{id}/start` creates a `WorkflowInstance` (if none) and schedules `run_workflow()` as a background task
3. **Execute**: `WorkflowEngine.run_workflow()` determines state → runs agents → transitions state → logs events
4. **Retry**: On failure, `BaseAgent.run_with_retry()` uses exponential backoff (base 1s, factor 2x). After `MAX_RETRIES=3` consecutive failures → `MANUAL_REVIEW` + alert
5. **Query**: Status/timeline endpoints read from `workflow_instances`, `agent_runs`, `event_logs`

## Key Design Decisions

### Sync SQLAlchemy + Async FastAPI
The app uses synchronous SQLAlchemy (sessionmaker) rather than async. FastAPI routes call `Depends(get_db)` which yields a session, commits on success, rolls back on exception. This avoids async session complexity while keeping the API non-blocking via background tasks for long-running workflows.

### Mock Agents (No Real Integration)
All four agents simulate their respective real-world actions without calling 美团/开店宝/企微 APIs. This keeps the system self-contained and testable.

### In-Memory Queue (No Redis)
Workflows are triggered via `asyncio.create_task()` in the background. For production scale, this should be replaced with a proper job queue (Celery, Dramatiq, or Redis-based). The TODO annotation marks this decision.

### State Validation
`VALID_TRANSITIONS` dict in `models.py` whitelists all legal from→to pairs. The engine's `_transition_state()` method checks against this before committing a state change.

### Event Log as Audit Trail
Every significant action (workflow creation, state change, agent run, report generation, manual takeover) writes an `EventLog` row. The timeline endpoint queries this table, providing a full chronological view without mutating workflow state.
