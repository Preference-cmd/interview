# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

A **multi-agent operations system** for 本地生活 (local life services) merchant operations on platforms like 美团/大众点评. The system automates the workflow of 代运营 (third-party operations) agents that manage merchant stores on these platforms.

Merchants use platforms like 美团 to reach local customers. 代运营 companies help merchants with store setup, marketing, review management, and data reporting. This system automates that workflow using AI agents.

## Tech Stack

- **Backend**: Python 3.12 + FastAPI + SQLAlchemy + SQLite (aiosqlite for async)
- **Frontend**: Next.js 16 (App Router, TypeScript)
- **Package Manager**: `uv` (backend), `pnpm` (frontend)
- **Testing**: pytest with pytest-asyncio

## Development Commands

```bash
# Backend
cd backend && make backend-install    # install deps (uv sync)
make backend-dev                      # run dev server (port 8000)
make backend-test                    # run tests
make backend-run                    # run production

# Frontend
make frontend-install               # pnpm install
make frontend-dev                   # pnpm run dev (port 3000)
make frontend-build                  # pnpm run build
```

Note: Always run `make backend-test` (not `cd backend && pytest`) because the test runner depends on `pyproject.toml`'s `pythonpath` setting.

## Architecture

### State Machine
```
NEW_STORE → DIAGNOSIS → FOUNDATION → DAILY_OPS → WEEKLY_REPORT → DONE
任意阶段异常 → MANUAL_REVIEW
```

### Four Mock Agents
| Agent | Responsibility | Delay | Failure Rate |
|-------|---------------|-------|-------------|
| AnalyzerAgent | Diagnose store + competitor data, output structured JSON with scores | — | 0% |
| WebOperatorAgent | Simulate backend actions (create deals, set promotions) | 1-3s | 20% |
| MobileOperatorAgent | Simulate App actions (material check, activity confirm) | 2-5s | 25% |
| ReporterAgent | Generate daily/weekly markdown reports with KPI summaries | — | 0% |

### Required APIs
- `POST /stores/import` — Batch import store data
- `POST /stores/{id}/start` — Start store workflow (background)
- `GET /stores/{id}/status` — Query current state + recent agent runs
- `GET /stores/{id}/timeline` — Query store event timeline
- `GET /dashboard/summary` — Global overview (state distribution, anomalies, queue backlog)
- `POST /stores/{id}/manual-takeover` — Trigger manual intervention
- `GET /alerts` — List all alerts
- `POST /alerts/{id}/acknowledge` — Acknowledge alert

## Directory Structure
```
backend/
├── main.py              # FastAPI entry, CORS configured
├── models.py           # SQLAlchemy models (6 tables)
├── schemas.py          # Pydantic schemas
├── database.py         # SQLite connection + Base
├── logging_config.py   # Structured logging setup
├── agents/
│   ├── base.py        # BaseAgent abstract class + retry logic
│   ├── analyzer.py    # AnalyzerAgent
│   ├── web_operator.py # WebOperatorAgent
│   ├── mobile_operator.py # MobileOperatorAgent
│   └── reporter.py    # ReporterAgent
├── orchestrator/
│   └── engine.py      # WorkflowEngine with state machine
└── pyproject.toml     # uv config
frontend/
├── app/
│   ├── page.tsx       # Dashboard (stores list, charts, alerts)
│   └── layout.tsx     # Root layout
├── components/
│   ├── StateBadge.tsx
│   ├── AlertList.tsx
│   ├── StoreList.tsx
│   ├── StoreTimeline.tsx
│   └── DashboardCharts.tsx  # PieChart, BarChart (recharts)
└── lib/
    ├── api.ts         # API client
    └── types.ts      # TypeScript types + constants
tests/
├── conftest.py       # pytest config + pythonpath
└── test_example.py   # 16 tests: state machine, engine, retry, manual takeover
mock_data/
├── stores.json       # 10 mock stores
├── competitors.json
└── reviews.json
Makefile
README.md             # Project overview
ARCHITECTURE.md       # Architecture diagram, state machine, data flow
AI_USAGE.md           # AI tool usage log
```

## Workflow Standards

- 使用 [superpowers workflow](https://github.com/anthropics/claude-code/tree/main/.claude/skills/superpowers) 进行开发：brainstorm → write-plan → execute → code-review → finish

## Frontend Design System

All frontend implementation **must** follow the design system specified in `frontend/DESIGN.md`. This file is the authoritative spec for visual design, color palette, typography, component styling, and layout principles.

## Important Implementation Notes

- All imports use **absolute paths** from the project root (e.g., `from backend.models import ...`, NOT `from models import ...`). This is critical for tests to work correctly.
- `metadata` is a reserved SQLAlchemy attribute — model fields use `extra_data` instead.
- `__table_args__ = {"extend_existing": True}` on all models for test compatibility.
- The `backend-test` Makefile target runs from `backend/` so `pyproject.toml`'s `pythonpath` is respected.
- SQLite database file is `backend/multi_agent_ops.db` (gitignored).
- The `doc/` directory is **gitignored** (contains reference materials).

## Important Constraints
- Mock agents do NOT need real 美团/开店宝/企微 integration — just mock behavior
- Frontend doesn't need to be visually polished — focus on information architecture
- Do NOT need real Redis — can use in-memory dict with `# TODO: replace with real Redis` annotation
