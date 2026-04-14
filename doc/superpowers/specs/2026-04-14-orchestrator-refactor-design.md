# Orchestrator 重构设计

**Date:** 2026-04-14
**Status:** Approved

## 背景

`backend/orchestrator/engine.py` (384行) 混合了 6 种不同职责：

1. Workflow 生命周期管理
2. Agent 编排与重试逻辑
3. 状态机（状态映射、状态转移）
4. 持久化（AgentRun、Report）
5. 事件/告警记录
6. Manual takeover 操作

单一职责原则被违反，导致难以独立测试和维护。

## 目标

- 将 `WorkflowEngine` 拆解为**组合结构**，各组件职责单一
- 通过依赖注入传递 Agent 实例，解耦 Engine 与 Agent 类型
- 保留 `WorkflowEngine` 作为唯一入口，保持现有 API 契约
- 路由层 (`routes/workflows.py`) 调整留待当前修改完成后进行

## 组件划分

| 组件 | 文件 | 职责 |
|------|------|------|
| `StateMachine` | `state_machine.py` | 状态转移逻辑、状态→Agent映射、next_state计算 |
| `EventEmitter` | `event_emitter.py` | 事件日志 + 告警持久化 |
| `AgentRunner` | `agent_runner.py` | Agent 调用、重试、结果处理 |
| `WorkflowEngine` | `engine.py` | 入口：编排流程、协调各组件、管理 session |

## 文件结构

```
backend/orchestrator/
├── __init__.py
├── engine.py          # WorkflowEngine（精简后的入口 ~80 行）
├── state_machine.py  # StateMachine 类 (~60 行)
├── event_emitter.py  # EventEmitter 类 (~50 行)
└── agent_runner.py    # AgentRunner 类 (~70 行)
```

## 详细设计

### 1. StateMachine (`state_machine.py`)

```python
class StateMachine:
    STATES_REQUIRING_ANALYZER = {WorkflowState.DIAGNOSIS}
    STATES_REQUIRING_WEB_OPS = {WorkflowState.FOUNDATION, WorkflowState.DAILY_OPS}
    STATES_REQUIRING_MOBILE_OPS = {WorkflowState.DAILY_OPS}
    STATES_REQUIRING_REPORTER = {WorkflowState.WEEKLY_REPORT}

    VALID_TRANSITIONS = VALID_TRANSITIONS  # 从 models 导入

    def get_agents_for_state(self, state: WorkflowState) -> list[str]: ...
    def get_next_state(self, current: WorkflowState) -> WorkflowState: ...
    def is_valid_transition(self, from_: WorkflowState, to: WorkflowState) -> bool: ...
    async def get_or_create_workflow(self, db: AsyncSession, store: Store) -> WorkflowInstance: ...
    async def transition(
        self, db: AsyncSession, store_id: int, wf: WorkflowInstance,
        from_state: WorkflowState, to_state: WorkflowState
    ) -> None: ...
    async def trigger_manual_takeover(self, db: AsyncSession, store: Store) -> WorkflowInstance: ...
```

### 2. EventEmitter (`event_emitter.py`)

```python
class EventEmitter:
    async def log_event(
        self, db: AsyncSession, store_id: int, event_type: str,
        from_state: str | None = None, to_state: str | None = None,
        agent_type: str | None = None, message: str | None = None,
        extra_data: dict | None = None,
    ) -> None: ...

    async def create_alert(
        self, db: AsyncSession, store_id: int,
        alert_type: str, severity: str, message: str,
        extra_data: dict | None = None,
    ) -> None: ...
```

### 3. AgentRunner (`agent_runner.py`)

```python
class AgentRunner:
    def __init__(self, agents: dict[str, BaseAgent]) -> None:
        self.agents = agents

    async def run(
        self, agent_type: str, context: dict, max_retries: int = 3
    ) -> tuple[dict, AgentResult]:
        """Run agent, update context, return result."""

    def _store_to_dict(self, store: Store) -> dict: ...  # 从 engine 移入
```

### 4. WorkflowEngine (`engine.py`) — 重构后

精简至 ~80 行，仅保留编排逻辑：

```python
class WorkflowEngine:
    MAX_RETRIES = 3

    def __init__(
        self,
        db: AsyncSession,
        state_machine: StateMachine,
        event_emitter: EventEmitter,
        agent_runner: AgentRunner,
    ) -> None:
        self.db = db
        self.sm = state_machine
        self.emitter = event_emitter
        self.runner = agent_runner

    async def run_workflow(self, store: Store) -> WorkflowInstance:
        # 编排逻辑，调用各组件
        ...
```

## Agent 依赖注入

Agent 实例由外部构造并注入 `AgentRunner`：

```python
# routes/workflows.py (待 routes 当前修改完成后调整)
agents = {
    "analyzer": AnalyzerAgent(),
    "web_operator": WebOperatorAgent(failure_rate=0.2),
    "mobile_operator": MobileOperatorAgent(failure_rate=0.25),
    "reporter": ReporterAgent(),
}
runner = AgentRunner(agents)
engine = WorkflowEngine(db=db, state_machine=sm, event_emitter=emitter, agent_runner=runner)
```

## 数据流

```
run_workflow(store)
  1. sm.get_or_create_workflow(store)
  2. agents = sm.get_agents_for_state(state)
  3. emitter.log_event(workflow_created, ...)
  4. for agent_type in agents:
       context, result = runner.run(agent_type, context)
       if result.failed:
         # 持久化 AgentRun (engine 层)
         break
  5. next_state = sm.get_next_state(state) or MANUAL_REVIEW
  6. if next_state != state:
       sm.transition(wf, from, to)
       emitter.log_event(state_change, ...)
  7. db.flush()
```

## 待后续处理

- `routes/workflows.py` 构造方式的调整（依赖注入 + Agent 实例化），留待当前 routes 修改完成后进行
