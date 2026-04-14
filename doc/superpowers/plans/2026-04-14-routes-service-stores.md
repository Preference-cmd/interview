# Backend Routes → Service → Stores 三层重构

> **For agentic workers:** 执行此计划建议使用 superpowers:subagent-driven-development。

**Goal:** 将 backend 拆分为清晰的三层：routes（HTTP 调度）→ service（业务编排）→ stores（数据访问）。Engine 保留在 `orchestrator/engine.py`。

**Architecture:** routes 只做 HTTP（参数提取 + response_model + HTTPException），service 编排业务逻辑和管理事务边界，stores 封装所有 SQL 查询和 model→schema 转换。

**Tech Stack:** Python 3.12 + FastAPI + SQLAlchemy async + Pydantic

---

## 新目录结构

```
backend/
├── routes/           # [不变] 薄 HTTP 层，调用 service
├── service/          # [新建] 业务逻辑编排
│   ├── store.py      # StoreService
│   ├── workflow.py   # WorkflowService
│   ├── dashboard.py  # DashboardService
│   └── alert.py      # AlertService
├── stores/           # [新建] 数据访问层（按 domain）
│   ├── store.py      # StoreStore — 查询/导入/列表
│   ├── workflow.py   # WorkflowStore — 工作流实例 + 状态分布
│   ├── alert.py      # AlertStore — 告警查询/确认
│   ├── agent_run.py  # AgentRunStore — agent 执行记录查询
│   └── event_log.py  # EventLogStore — 事件日志查询
├── orchestrator/     # [不变] WorkflowEngine
├── models/           # [不变] SQLAlchemy models
└── schemas/          # [不变] Pydantic schemas
```

---

## 详细设计

### Stores 层

每个 store 接受 `AsyncSession` 参数。核心职责：SQL 查询封装（JOIN/filter/limit）、model → Pydantic schema 转换。

#### `stores/store.py` — StoreStore

```python
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import Store
from backend.schemas import StoreImportItem, StoreResponse

class StoreStore:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, store_id: int) -> Store | None:
        return await self._session.get(Store, store_id)

    async def import_or_update(self, items: list[StoreImportItem]) -> list[Store]:
        """批量 upsert：存在则更新，不存在则创建"""
        ...

    async def list_all(self) -> list[Store]:
        ...
```

#### `stores/workflow.py` — WorkflowStore

```python
class WorkflowStore:
    async def get_by_store_id(self, store_id: int) -> WorkflowInstance | None: ...
    async def get_state_distribution(self) -> dict[str, int]: ...
    async def get_manual_review_queue(self) -> list[tuple[WorkflowInstance, Store]]: ...
```

#### `stores/alert.py` — AlertStore

```python
class AlertStore:
    async def list_recent(self, limit: int = 20) -> list[Alert]: ...
    async def count_unacknowledged(self) -> int: ...
    async def acknowledge(self, alert_id: int) -> bool: ...
```

#### `stores/agent_run.py` — AgentRunStore

```python
class AgentRunStore:
    async def list_recent(self, store_id: int | None, limit: int) -> list[AgentRun]: ...
```

#### `stores/event_log.py` — EventLogStore

```python
class EventLogStore:
    async def list_by_store(self, store_id: int, limit: int) -> list[EventLog]: ...
```

### Service 层

每个 service 管理事务边界。`start_workflow` / `manual_takeover` 使用独立 `AsyncSessionLocal`（保持原有设计）。

#### `service/store.py` — StoreService

```python
class StoreService:
    def __init__(self, session: AsyncSession, store_store: StoreStore):
        self._session = session
        self._store = store_store

    async def import_stores(self, request: StoreImportRequest) -> list[StoreResponse]:
        stores = await self._store.import_or_update(request.stores)
        await self._session.commit()
        return [StoreResponse.model_validate(s) for s in stores]

    async def list_stores(self) -> list[StoreResponse]:
        stores = await self._store.list_all()
        return [StoreResponse.model_validate(s) for s in stores]
```

#### `service/workflow.py` — WorkflowService

```python
class WorkflowService:
    def __init__(self, session: AsyncSession, store_store: StoreStore,
                 workflow_store: WorkflowStore, agent_run_store: AgentRunStore,
                 event_log_store: EventLogStore,
                 state_machine: StateMachine, event_emitter: EventEmitter,
                 agent_runner: AgentRunner):
        ...

    async def get_store_detail(self, store_id: int) -> StoreResponse:
        # 找不到抛 HTTPException(404)

    async def get_status(self, store_id: int) -> WorkflowStatusResponse:
        # 并发查 store + workflow + recent_runs，组装 schema

    async def get_timeline(self, store_id: int) -> TimelineResponse:
        # 查 workflow（取 current_state）+ event_logs，组装 schema

    async def start_workflow(self, store_id: int) -> dict[str, int | str]:
        # 独立 AsyncSessionLocal，管理 commit/rollback

    async def manual_takeover(self, store_id: int) -> dict[str, int | str]:
        # 调用 engine.trigger_manual_takeover，管理 commit/rollback
```

#### `service/dashboard.py` — DashboardService

并发执行所有查询，聚合后返回 `DashboardSummaryResponse`。

#### `service/alert.py` — AlertService

```python
class AlertService:
    def __init__(self, session: AsyncSession, alert_store: AlertStore):
        self._session = session
        self._alert = alert_store

    async def list_alerts(self) -> list[AlertResponse]: ...
    async def acknowledge(self, alert_id: int) -> dict[str, int | str]: ...
```

### Routes 层

移除所有 DB 查询、手动序列化、`await db.commit()`，仅保留 HTTP 职责。

---

## 实施计划

### Task 1: 创建 stores/ 数据访问层

- [ ] 新建 `backend/stores/__init__.py`
- [ ] 新建 `backend/stores/store.py` — StoreStore
- [ ] 新建 `backend/stores/workflow.py` — WorkflowStore
- [ ] 新建 `backend/stores/alert.py` — AlertStore
- [ ] 新建 `backend/stores/agent_run.py` — AgentRunStore
- [ ] 新建 `backend/stores/event_log.py` — EventLogStore

### Task 2: 创建 service/ 服务编排层

- [ ] 新建 `backend/service/__init__.py`
- [ ] 新建 `backend/service/store.py` — StoreService
- [ ] 新建 `backend/service/workflow.py` — WorkflowService
- [ ] 新建 `backend/service/dashboard.py` — DashboardService
- [ ] 新建 `backend/service/alert.py` — AlertService

### Task 3: 重构 routes/ 调用 service

- [ ] 重写 `backend/routes/stores.py` — 调用 StoreService
- [ ] 重写 `backend/routes/workflows.py` — 调用 WorkflowService
- [ ] 重写 `backend/routes/dashboard.py` — 调用 DashboardService
- [ ] 重写 `backend/routes/alerts.py` — 调用 AlertService

### Task 4: 验证

```bash
make backend-test   # 42 passed
make backend-dev    # 启动无报错
```

---

## 关键文件变更

| 操作 | 文件 |
|---|---|
| 新建 | `backend/stores/__init__.py` |
| 新建 | `backend/stores/store.py` |
| 新建 | `backend/stores/workflow.py` |
| 新建 | `backend/stores/alert.py` |
| 新建 | `backend/stores/agent_run.py` |
| 新建 | `backend/stores/event_log.py` |
| 新建 | `backend/service/__init__.py` |
| 新建 | `backend/service/store.py` |
| 新建 | `backend/service/workflow.py` |
| 新建 | `backend/service/dashboard.py` |
| 新建 | `backend/service/alert.py` |
| 修改 | `backend/routes/stores.py` |
| 修改 | `backend/routes/workflows.py` |
| 修改 | `backend/routes/dashboard.py` |
| 修改 | `backend/routes/alerts.py` |