# 开发状态追踪

> 最后更新：2026-04-15

## 决策记录

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-04-14 | 使用 `asyncio.create_task()` 触发后台 workflow | 轻量，无需引入 Celery/Redis |
| 2026-04-14 | 所有 agent 均为 mock | 无真实美团/开店宝/企微 接入需求 |
| 2026-04-14 | Frontend: Tailwind CSS v4 + shadcn/ui | Modern CSS tooling, design system in `frontend/DESIGN.md` |
| 2026-04-14 | Frontend 设计规范存放于 `doc/specs/` | 与源码分离，便于独立演进 |
| 2026-04-14 | Backend: SQL migration 系统替代 `create_all` | 支持生产环境 schema 演进 |
| 2026-04-14 | Backend: 全面 async 化 + 模块化拆分 | 统一 sync/async 混乱现状 |

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
| `components/StoreList.tsx` | 店铺列表（表格） |
| `components/StoreTimeline.tsx` | 店铺时间线 |
| `components/DashboardCharts.tsx` | PieChart + BarChart (recharts) |
| `lib/api.ts` | API 客户端 |
| `lib/types.ts` | TypeScript 类型 |
| `lib/utils.ts` | 工具函数（cn） |

### shadcn/ui 状态
- `components.json` 已配置，style: default，icons: lucide
- **0 个组件添加**，当前所有组件均为手写

### 进行中
| Feature | Spec/Plan | 状态 |
|---------|------|------|
| Store Detail Page | `superpowers/specs/STORE-DETAIL-DESIGN.md` | 设计完成，待实现 |

### 技术债务
```
# TODO: shadcn 组件引入 — 需 theming 到 Anthropic 暖色调
```

---

## Backend 状态

### 测试
```
16 passed, 0 warnings
- 6 state transition tests
- 5 workflow engine tests (async)
- 2 retry logic tests
- 2 manual takeover tests (async)
- 1 reporter idempotency test
```

### 新目录结构
```
backend/
├── main.py                    # FastAPI app — router registration + lifespan
├── database/
│   ├── __init__.py            # Re-exports Base, async_engine, AsyncSessionLocal, get_db
│   ├── base.py                # declarative Base
│   └── session.py             # async_engine + AsyncSessionLocal + get_db (async)
├── models/
│   ├── __init__.py            # Re-exports all models and enums
│   ├── _enums.py              # WorkflowState, AgentStatus, VALID_TRANSITIONS
│   ├── store.py               # Store model
│   ├── workflow.py            # WorkflowInstance model
│   ├── agent_run.py           # AgentRun model
│   ├── event_log.py           # EventLog model
│   ├── alert.py               # Alert model
│   └── report.py              # Report model
├── schemas/
│   ├── __init__.py            # Re-exports all schemas
│   ├── store.py               # StoreImportRequest/Response
│   ├── workflow.py            # WorkflowStatusResponse, DashboardSummaryResponse
│   ├── agent.py               # AgentRunResponse
│   └── timeline.py            # EventLogResponse, TimelineResponse
├── routes/
│   ├── __init__.py            # Re-exports all routers
│   ├── stores.py              # /stores/import, /stores (GET)
│   ├── workflows.py           # /stores/{id}/* (all workflow routes)
│   ├── dashboard.py           # /dashboard/summary
│   └── alerts.py              # /alerts, /alerts/{id}/acknowledge
├── agents/                    # 4 mock agents (analyzer, web_operator, mobile_operator, reporter)
├── orchestrator/
│   └── engine.py              # WorkflowEngine — fully async
├── migrations/
│   ├── __init__.py
│   ├── runner.py              # MigrationRunner
│   ├── __main__.py           # CLI: python -m migrations
│   └── sql/
│       └── 0001_initial_schema.sql
└── logging_config.py
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

| # | 文件 | 问题 | 建议 |
|---|------|------|------|
| 1 | `migrations/runner.py:52` | SQL 按 `;` 分割无法处理字符串内含分号（如 `VALUES ('a;b')`） | 改用正则或 tokenizer；或当前 migration SQL 均不含内部分号，暂可接受 |
| 2 | `migrations/runner.py:50-60` | 无事务包裹，migration 执行中途失败会留下半应用状态 | 可接受（当前 migration 均为 `CREATE TABLE IF NOT EXISTS`，天然幂等）；若未来添加破坏性 SQL 需改为原子事务 |
| 3 | `migrations/runner.py:46-48` | `except Exception` 吞噬所有错误（网络、权限等）被误判为"无 migration" | 改用 `except OperationalError` 仅捕获"表不存在" |
| 4 | `migrations/runner.py:19-31` | `run_pending` 中 check 和 apply 之间无锁，并发多进程可能重复执行 migration | 可接受（SQLite 单进程 + aiosqlite 无并发问题）；`INSERT OR IGNORE` 防止重复写入 |
| 5 | `orchestrator/engine.py:322,339` | `_log_event` 和 `_create_alert` 只 `add()` 不 `flush()`，若单独调用数据静默丢失 | 改为 `flush()` 确保持久化；当前所有调用处都有后续 flush，暂不紧急 |
| 6 | `routes/workflows.py:48-59` | `start_workflow` 丢弃注入的 `db`，自行创建 `AsyncSessionLocal` | 可接受（engine 需要独立 session）；未来如需事务传播需重构 |
| 7 | `test_example.py` | 无端到端失败路径测试（`run_workflow` + agent 失败 + `retry_count` 验证） | 添加 `TestWorkflowEngineFailure` 类 |

#### Low

| # | 文件 | 问题 |
|---|------|------|
| 8 | `agents/base.py` + `models/_enums.py` | `AgentStatus` 各定义了一份，值相同但非同一类 |
| 9 | `routes/workflows.py:8` | `AsyncSessionLocal` 导入但未使用（`start_workflow` 中 `db` 参数被丢弃） |
| 10 | `routes/stores.py:32` | `datetime` 在循环体内导入，应放函数顶部 |
| 11 | `test_example.py:22-27` | `engine_sqlite` fixture 孤立，仅服务 sync state machine 测试（不实际调用 DB） |

### 技术债务
```
# TODO: replace with real Redis  (engine.py — 内存队列替代方案标注)
# TODO: Alembic 替代手写 SQL migrations (if project scales beyond SQLite)
# TODO: 并发竞态 — 两个并发 /stores/{id}/start 可能同时创建 workflow
# TODO: 代码评审 — 上表 Medium #1-7, Low #8-11
```
