# Multi-Agent Ops

本地生活商户多智能体运营系统。自动化代运营团队在美团/大众点评平台上的工作流：门店诊断 → 基建完善 → 日常运营 → 周报复盘。

## Tech Stack

| Layer | Technology |
|------|------------|
| Backend | Python 3.12 + FastAPI + SQLAlchemy + SQLite |
| Frontend | Next.js 16 (App Router, TypeScript) |
| Package Manager | `uv` (backend), `pnpm` (frontend) |
| Testing | pytest + pytest-asyncio |

## Quick Start

```bash
# Backend
make backend-install
make backend-dev      # http://localhost:8000

# Frontend
make frontend-install
make frontend-dev    # http://localhost:3000

# Tests
make backend-test
```

## Architecture

### State Machine

```
NEW_STORE → DIAGNOSIS → FOUNDATION → DAILY_OPS → WEEKLY_REPORT → DONE
任意阶段异常 → MANUAL_REVIEW
```

### Four Agents

| Agent | Responsibility |
|-------|---------------|
| AnalyzerAgent | 诊断门店+竞品数据，输出评分与建议 |
| WebOperatorAgent | 模拟后台操作（建团单/设推广），1-3s 延迟，20% 失败率 |
| MobileOperatorAgent | 模拟 App 操作（素材检查/活动确认），2-5s 延迟，25% 失败率 |
| ReporterAgent | 生成日报/周报（Markdown + JSON） |

### API Endpoints

- `POST /stores/import` — 批量导入门店
- `POST /stores/{id}/start` — 启动工作流（后台异步）
- `GET /stores/{id}/status` — 查询状态与最近执行记录
- `GET /stores/{id}/timeline` — 查询事件时间线
- `GET /dashboard/summary` — 全局概览
- `POST /stores/{id}/manual-takeover` — 人工接管
- `GET /alerts` — 告警列表
- `POST /alerts/{id}/acknowledge` — 确认告警

## Project Structure

```
backend/
├── main.py              # FastAPI 入口
├── models.py           # SQLAlchemy 模型（6 张表）
├── schemas.py          # Pydantic schemas
├── database.py        # SQLite 连接
├── logging_config.py   # 结构化日志
├── agents/
│   ├── base.py        # BaseAgent + 重试逻辑
│   ├── analyzer.py    # AnalyzerAgent
│   ├── web_operator.py # WebOperatorAgent
│   ├── mobile_operator.py # MobileOperatorAgent
│   └── reporter.py    # ReporterAgent
└── orchestrator/
    └── engine.py      # WorkflowEngine 状态机

frontend/
├── app/               # Next.js App Router pages
├── components/        # React 组件
└── lib/               # API client + types

tests/                 # pytest 测试
mock_data/             # 模拟门店/竞品/评价数据
```
