# doc/ — Project Documentation

> 本目录包含项目开发过程中积累的文档，与源码分离管理。

## Full Index

### 目录结构
```
doc/
├── README.md                    ← 你在这里
├── STATE.md                     ← 开发状态追踪（决策记录 + Backend/Frontend 状态）
├── reference/                   ← 原始需求参考
│   ├── AI 编程机试.md
│   └── 本地生活业务基础知识.md
└── superpowers/                 ← superpowers workflow 产物
    ├── specs/                   ← Feature 设计规范
    │   └── STORE-DETAIL-DESIGN.md
    └── plans/                   ← Feature 实现计划
```

### 文件说明

| 文件 | 说明 | 维护频率 |
|------|------|----------|
| `README.md` | 本文档，doc/ 索引入口 | 按需 |
| `STATE.md` | 开发状态追踪：决策记录、Backend/Frontend 当前状态、已知问题 | 按需 |
| `reference/AI 编程机试.md` | 原始需求规格 | 静态 |
| `reference/本地生活业务基础知识.md` | 业务背景资料 | 静态 |
| `superpowers/specs/STORE-DETAIL-DESIGN.md` | 店铺详情页设计规范 | 设计阶段更新 |
| `superpowers/plans/2026-04-14-sql-migrations.md` | SQL migration 系统 | Plan 1 |
| `superpowers/plans/2026-04-14-database-models-schemas.md` | 模块化 models/schemas + async DB 层 | Plan 2 |
| `superpowers/plans/2026-04-14-routes-engine-async.md` | routes 模块化 + Engine async + retry_count 修复 | Plan 3 |

## Tech Stack

- **Frontend**: Next.js 16 + Tailwind CSS v4 + shadcn/ui + recharts
- **Backend**: Python 3.12 + FastAPI + SQLAlchemy + SQLite

## Design Specs & Plans

设计规范和实现计划按功能模块组织。实现前必须先查阅对应规范。

| Feature | Spec | Plan |
|---------|------|------|
| Store Detail Page | `superpowers/specs/STORE-DETAIL-DESIGN.md` | `superpowers/plans/` |
| Backend async + modularization | — | `superpowers/plans/2026-04-14-*.md` (Plans 1-3) |
| Backend 三层架构 | — | `superpowers/plans/2026-04-14-routes-service-stores.md` |
