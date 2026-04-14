# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

A **multi-agent operations system** for 本地生活 (local life services) merchant operations on platforms like 美团/大众点评. The system automates the workflow of 代运营 (third-party operations) agents that manage merchant stores on these platforms.

## Tech Stack

- **Backend**: Python 3.12 + FastAPI + SQLAlchemy + SQLite (aiosqlite for async)
- **Frontend**: Next.js 16 (App Router, TypeScript) + Tailwind CSS v4 + shadcn/ui
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

### Directory Structure
```
backend/              # FastAPI + SQLAlchemy + SQLite (see backend/main.py)
frontend/
├── app/
│   ├── page.tsx       # Dashboard
│   ├── layout.tsx     # Root layout
│   └── stores/[id]/page.tsx   # Store detail (see doc/README.md)
├── components/        # UI components
└── lib/               # API client, types
tests/                 # pytest (conftest.py, test_example.py)
mock_data/             # JSON fixtures
Makefile
```

## Workflow Standards

使用 [superpowers workflow](https://github.com/anthropics/claude-code/tree/main/.claude/skills/superpowers) 进行开发：brainstorm → write-plan → execute → code-review → finish

## Frontend

All frontend implementation follows `frontend/DESIGN.md` (color palette, typography, component styling). Design specs and implementation plans are in `doc/README.md`. 实现前必须先查阅对应规范，确保实现符合设计意图。

## Important Implementation Notes

- All imports use **absolute paths** from the project root (e.g., `from backend.models import ...`, NOT `from models import ...`). This is critical for tests to work correctly.
- `metadata` is a reserved SQLAlchemy attribute — model fields use `extra_data` instead.
- `__table_args__ = {"extend_existing": True}` on all models for test compatibility.
- The `backend-test` Makefile target runs from `backend/` so `pyproject.toml`'s `pythonpath` is respected.
- SQLite database file is `backend/multi_agent_ops.db` (gitignored).
- The `doc/` directory is **not gitignored** — contains versioned design specs and plans.

## Important Constraints

- Mock agents do NOT need real 美团/开店宝/企微 integration — just mock behavior
- Frontend doesn't need to be visually polished — focus on information architecture
- Do NOT need real Redis — can use in-memory dict with `# TODO: replace with real Redis` annotation
