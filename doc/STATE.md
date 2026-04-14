# 开发状态追踪

> 最后更新：2026-04-14

## 决策记录

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-04-14 | 使用 sync SQLAlchemy 而非 async | SQLite + 单线程场景下 sync 足够，避免 async 复杂度 |
| 2026-04-14 | 使用 `asyncio.create_task()` 触发后台 workflow | 轻量，无需引入 Celery/Redis |
| 2026-04-14 | 所有 agent 均为 mock | 无真实美团/开店宝/企微 接入需求 |
| 2026-04-14 | Frontend: Tailwind CSS v4 + shadcn/ui | Modern CSS tooling, design system in `frontend/DESIGN.md` |
| 2026-04-14 | Frontend 设计规范存放于 `doc/specs/` | 与源码分离，便于独立演进 |

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
| Feature | Spec | 状态 |
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
- 5 workflow engine tests
- 2 retry logic tests
- 2 manual takeover tests
- 1 reporter idempotency test
```

### 技术债务
```
# TODO: replace with real Redis  (engine.py — 内存队列替代方案标注)
# TODO: upgrade to full async DB session (database.py — AsyncSessionLocal 未使用)
```

### 已知问题

| 优先级 | 问题 | 说明 |
|--------|------|------|
| P0 | `workflow_instances.store_id` 缺唯一约束 | 并发创建可能产生多条记录 |
| P0 | 缺关键查询索引 | `agent_runs`, `event_logs`, `alerts`, `reports` 需索引 |
| P1 | 数据库层 sync/async 不一致 | `AsyncSessionLocal` 未使用，`get_db()` 产出 sync Session |
| P1 | `AgentRun.retry_count` 永远是 0 | `engine.py` 写死为 0 |
| P1 | 并发竞态 | 两个并发 `/stores/{id}/start` 可能同时创建 workflow |
