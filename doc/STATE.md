# 开发状态追踪

> 最后更新：2026/04/14

## 决策记录

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-04-14 | 使用 `asyncio.create_task()` 触发后台 workflow | 轻量，无需引入 Celery/Redis |
| 2026-04-14 | 所有 agent 均为 mock | 无真实美团/开店宝/企微 接入需求 |
| 2026-04-14 | Frontend: Tailwind CSS v4 + shadcn/ui | Modern CSS tooling, design system in `frontend/DESIGN.md` |
| 2026-04-14 | Frontend 设计规范存放于 `doc/specs/` | 与源码分离，便于独立演进 |
| 2026-04-14 | Backend: SQL migration 系统替代 `create_all` | 支持生产环境 schema 演进 |
| 2026-04-14 | Backend: 全面 async 化 + 模块化拆分 | 统一 sync/async 混乱现状 |
| 2026-04-14 | Backend: routes → service → stores 三层架构 | 路由薄化、业务逻辑下沉、数据访问封装 |

---

## Frontend 状态

### 技术栈
Next.js 16 + Tailwind CSS v4 + shadcn/ui + recharts

### 设计系统
`frontend/DESIGN.md` — Anthropic 暖色调设计系统（parchment/ivory/terracotta 调色板）

### 现有页面/组件
| 文件 | 说明 |
|------|------|
| `app/page.tsx` | Dashboard，3 Tab（概览/店铺列表/告警） |
| `app/layout.tsx` | Root layout |
| `components/StateBadge.tsx` | 工作流状态徽章 |
| `components/AlertList.tsx` | 告警列表 |
| `components/StoreList.tsx` | 店铺列表（表格，点击行打开详情） |
| `components/StoreTimeline.tsx` | 店铺时间线 |
| `components/StoreDetailModal.tsx` | 店铺详情模态浮层 |
| `components/WorkflowStepper.tsx` | 垂直工作流步骤条 |
| `components/StepDetailCard.tsx` | 当前步骤详情卡片 |
| `components/FailureLogCard.tsx` | 失败日志卡片（MANUAL_REVIEW） |
| `components/VerticalTimeline.tsx` | 垂直动态时间线 |
| `components/DashboardCharts.tsx` | PieChart + BarChart (recharts) |
| `lib/api.ts` | API 客户端 |
| `lib/types.ts` | TypeScript 类型 |
| `lib/utils.ts` | 工具函数（cn） |

### shadcn/ui 状态
- `components.json` 已配置，style: default，icons: lucide
- **0 个组件添加**，当前所有组件均为手写

### 进行中
（无）

### 已完成 (2026-04-14)
| Feature | Spec/Plan | 状态 |
|---------|------|------|
| Store Detail Modal | `superpowers/plans/2026-04-14-store-detail-modal-plan.md` | 实现完成 |
| **状态自动流转（带延迟）** | `superpowers/plans/2026-04-14-auto-state-transition-plan.md` | 实现完成 |

### 技术债务
```
# TODO: shadcn 组件引入 — 需 theming 到 Anthropic 暖色调
```

---

## Backend 状态

### 测试
```
46 passed, 0 errors
- 7 agent_runner tests
- 4 event_emitter tests
- 9 workflow_engine tests
- 18 state_machine tests
- 1 agent_run_store test
- 5 workflow_store tests
- 2 report_store tests
```

### 新目录结构
```
backend/
├── main.py                    # FastAPI app — router registration + lifespan
├── database.py               # SQLAlchemy async engine + session setup
├── logging_config.py
├── models/
│   ├── __init__.py           # Re-exports all models and enums
│   ├── _enums.py             # WorkflowState, AgentStatus, VALID_TRANSITIONS
│   ├── store.py              # Store model
│   ├── workflow.py           # WorkflowInstance model
│   ├── agent_run.py          # AgentRun model
│   ├── event_log.py          # EventLog model
│   ├── alert.py              # Alert model
│   └── report.py             # Report model
├── schemas/
│   ├── __init__.py           # Re-exports all schemas
│   ├── store.py              # StoreImportRequest/Response
│   ├── workflow.py           # WorkflowStatusResponse, DashboardSummaryResponse
│   ├── agent.py              # AgentRunResponse
│   └── timeline.py          # EventLogResponse, TimelineResponse
├── routes/                    # HTTP 层 — 仅做参数提取和 response_model
│   ├── __init__.py
│   ├── stores.py             # /stores/import, /stores (GET)
│   ├── workflows.py          # /stores/{id}/* (detail/start/status/timeline/manual-takeover)
│   ├── dashboard.py          # /dashboard/summary
│   └── alerts.py             # /alerts, /alerts/{id}/acknowledge
├── service/                   # 服务层 — 业务编排 + 事务边界
│   ├── __init__.py
│   ├── store.py              # StoreService
│   ├── workflow.py           # WorkflowService
│   ├── dashboard.py          # DashboardService
│   └── alert.py              # AlertService
├── stores/                    # 数据访问层 — SQL 查询封装
│   ├── __init__.py
│   ├── store.py              # StoreStore
│   ├── workflow.py           # WorkflowStore (extended with create/get/transition/update methods)
│   ├── alert.py              # AlertStore
│   ├── agent_run.py          # AgentRunStore (extended with create_agent_run)
│   ├── event_log.py          # EventLogStore
│   └── report.py             # ReportStore (NEW — create_report)
├── orchestrator/              # 工作流编排（无直接 DB 访问）
│   ├── engine.py             # WorkflowEngine — orchestration entry point (197 lines, no self.db)
│   ├── state_machine.py     # Pure stateless state transitions (39 lines)
│   ├── event_emitter.py      # Thin db.add() wrapper (21 lines)
│   └── agent_runner.py       # Agent dispatch with retry (77 lines)
├── agents/                    # 4 mock agents (AnalyzerAgent, WebOperatorAgent, MobileOperatorAgent, ReporterAgent)
├── migrations/
│   ├── __init__.py
│   ├── runner.py             # MigrationRunner
│   ├── __main__.py          # CLI: python -m migrations
│   └── sql/
│       └── 0001_initial_schema.sql
└── tests/                     # pytest (conftest.py, test_*.py)
    ├── conftest.py
    ├── test_state_machine.py
    ├── test_event_emitter.py
    ├── test_orchestrator_engine.py
    ├── test_agent_runner.py
    ├── test_workflow_store.py
    ├── test_agent_run_store.py
    ├── test_report_store.py
    └── test_*.py             # Other integration tests
```

### 已知问题

| 优先级 | 问题 | 说明 | 状态 |
|--------|------|------|------|
| P0 | `workflow_instances.store_id` 缺唯一约束 | 并发创建可能产生多条记录 | ✅ 已修复 |
| P0 | 缺关键查询索引 | `agent_runs`, `event_logs`, `alerts`, `reports` 需索引 | ✅ 已修复 |
| P1 | 数据库层 sync/async 不一致 | `AsyncSessionLocal` 未使用，`get_db()` 产出 sync Session | ✅ Plan 1 已修复 |
| P1 | `AgentRun.retry_count` 永远是 0 | `engine.py` 写死为 0 | ✅ Plan 3 已修复 — `AgentResult.attempts` 字段追踪重试次数 |
| P1 | 并发竞态 | 两个并发 `/stores/{id}/start` 可能同时创建 workflow | 待修复 |

### 代码评审 — 待修复

#### Medium

| # | 文件 | 问题 | 建议 | 状态 |
|---|------|------|------|------|
| 1 | `migrations/runner.py:52` | SQL 按 `;` 分割无法处理字符串内含分号（如 `VALUES ('a;b')`） | 改用正则或 tokenizer；或当前 migration SQL 均不含内部分号，暂可接受 | — |
| 2 | `migrations/runner.py:50-60` | 无事务包裹，migration 执行中途失败会留下半应用状态 | 可接受（当前 migration 均为 `CREATE TABLE IF NOT EXISTS`，天然幂等）；若未来添加破坏性 SQL 需改为原子事务 | — |
| 3 | `migrations/runner.py:46-48` | `except Exception` 吞噬所有错误（网络、权限等）被误判为"无 migration" | 改用 `except OperationalError` 仅捕获"表不存在" | — |
| 4 | `migrations/runner.py:19-31` | `run_pending` 中 check 和 apply 之间无锁，并发多进程可能重复执行 migration | 可接受（SQLite 单进程 + aiosqlite 无并发问题）；`INSERT OR IGNORE` 防止重复写入 | — |
| 5 | `orchestrator/engine.py` | `_log_event` 和 `_create_alert` 只 `add()` 不 `flush()`，若单独调用数据静默丢失 | 改为 `flush()` 确保持久化 | ✅ 已废弃 — Phase 2 后 engine 不再直接调用 `db.add()`，统一经由 stores/EventEmitter |
| 6 | `routes/workflows.py:48-59` | `start_workflow` 丢弃注入的 `db`，自行创建 `AsyncSessionLocal` | 可接受（engine 需要独立 session）；未来如需事务传播需重构 | — |
| 7 | `test_example.py` | 无端到端失败路径测试（`run_workflow` + agent 失败 + `retry_count` 验证） | 添加 `TestWorkflowEngineFailure` 类 | — |

#### Low

| # | 文件 | 问题 | 状态 |
|---|------|------|------|
| 8 | `agents/base.py` + `models/_enums.py` | `AgentStatus` 各定义了一份，值相同但非同一类 | ✅ 已缓解 — `agents/base.py` 添加 `AgentResultStatus = AgentStatus` alias，代码中统一使用 alias |
| 9 | `routes/workflows.py` | `AsyncSessionLocal` 导入但未使用 | ✅ 已废弃 — Phase 2 后 routes 统一由 `WorkflowService` 持有 stores，不再有未使用导入 |
| 10 | `routes/stores.py` | `datetime` 在循环体内导入 | ✅ 已废弃 — routes 已被重构，原问题位置不存在 |
| 11 | `test_example.py` | `engine_sqlite` fixture 孤立，仅服务 sync state machine 测试 | ✅ 已废弃 — 测试文件重构，孤立 fixture 已移除 |

### 技术债务
```
# TODO: replace with real Redis  (engine.py — 内存队列替代方案标注)
# TODO: Alembic 替代手写 SQL migrations (if project scales beyond SQLite)
# TODO: 并发竞态 — 两个并发 /stores/{id}/start 可能同时创建 workflow
# TODO: 代码评审 — 上表 Medium #1-4, #6-7 未处理，Medium #5 已废弃，Low #8-11 已处理
```
