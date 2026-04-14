# Orchestrator DB 分离计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `StateMachine` 转为纯无状态类，将 `Engine` 中的所有 `db.add`/`db.flush` 移入 stores 层，消除 orchestrator 对 DB session 的直接依赖。

**Architecture:** 三层分离：
- **orchestrator** — 纯业务逻辑（状态映射、Agent调度、事件构造），无 DB 依赖
- **stores** — 所有 DB 持久化操作（WorkflowStore、AgentRunStore、ReportStore）
- **service** — 依赖注入编排层（OrchestratorService 持有所有组件 + stores）

**Tech Stack:** Python 3.12 + pytest-asyncio + unittest.mock + Ruff

---

## 文件变更总览

| 操作 | 文件 |
|------|------|
| 修改 | `backend/orchestrator/state_machine.py` — 删除 async DB 方法，精简为纯函数类 |
| 修改 | `backend/orchestrator/event_emitter.py` — 改接收 model 实例，仅做 `db.add` |
| 修改 | `backend/orchestrator/engine.py` — 注入 stores，移除所有 `db.add`/`db.flush` |
| 修改 | `backend/stores/workflow.py` — 添加 create/get_or_create/transition/trigger_manual_takeover/update_timestamp |
| 修改 | `backend/stores/agent_run.py` — 添加 create_agent_run |
| 新建 | `backend/stores/report.py` — 新建 ReportStore |
| 修改 | `backend/stores/__init__.py` — 导出 ReportStore |
| 修改 | `backend/service/workflow.py` — 添加 ReportStore 注入 |
| 修改 | `backend/routes/workflows.py` — `_build_workflow_service` 添加 ReportStore |
| 修改 | `tests/test_orchestrator_engine.py` — 更新 mock 路径 |
| 修改 | `tests/test_state_machine.py` — 删除已迁移的 async 测试 |

---

## 新接口设计

### StateMachine（精简后）

```python
class StateMachine:
    # 纯数据映射，无状态
    STATES_REQUIRING_ANALYZER: set[WorkflowState]
    STATES_REQUIRING_WEB_OPS: set[WorkflowState]
    STATES_REQUIRING_MOBILE_OPS: set[WorkflowState]
    STATES_REQUIRING_REPORTER: set[WorkflowState]

    def get_agents_for_state(state: WorkflowState) -> list[str]: ...
    def get_next_state(current: WorkflowState) -> WorkflowState: ...
    def is_valid_transition(from_: WorkflowState, to: WorkflowState) -> bool: ...
```

### EventEmitter（重构后）

```python
class EventEmitter:
    def __init__(self, db) -> None:
        self._db = db

    def emit_event(self, event: EventLog) -> None: ...
    def emit_alert(self, alert: Alert) -> None: ...
```

### 新增/扩展的 Store 方法

```python
# WorkflowStore — 新增方法
async def create_workflow(store_id: int) -> WorkflowInstance
async def get_or_create_workflow(store_id: int) -> WorkflowInstance
async def transition_workflow(
    wf: WorkflowInstance, from_state: WorkflowState, to_state: WorkflowState
) -> None
async def trigger_manual_takeover(wf: WorkflowInstance) -> WorkflowInstance
async def update_timestamp(wf: WorkflowInstance) -> None

# AgentRunStore — 新增方法
async def create_agent_run(...) -> AgentRun  # 返回含 id 的实例

# ReportStore — 新建
class ReportStore:
    async def create_report(...) -> Report  # 返回含 id 的实例
```

### Engine 注入（重构后）

```python
class WorkflowEngine:
    def __init__(
        self,
        workflow_store: WorkflowStore,
        agent_run_store: AgentRunStore,
        report_store: ReportStore,
        state_machine: StateMachine,
        event_emitter: EventEmitter,
        agent_runner: AgentRunner,
    ) -> None:
```

**注意：** `db` 不再作为独立参数，而是分散到各个 Store 实例中。

---

## Task 1: 扩展 WorkflowStore

**Files:**
- Modify: `backend/stores/workflow.py`
- Test: `tests/test_workflow_store.py` (新建)

- [ ] **Step 1: 创建 `tests/test_workflow_store.py`**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.models._enums import WorkflowState
from backend.models import WorkflowInstance


def _make_session():
    sess = MagicMock()
    sess.execute = AsyncMock()
    sess.add = MagicMock()
    sess.flush = AsyncMock()
    return sess


class TestCreateWorkflow:
    async def test_creates_workflow_instance(self):
        from backend.stores.workflow import WorkflowStore

        sess = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        sess.execute.return_value = mock_result

        store = WorkflowStore(sess)
        wf = await store.create_workflow(store_id=1)

        assert wf.store_id == 1
        assert wf.current_state == WorkflowState.NEW_STORE.value
        assert wf.consecutive_failures == 0
        sess.add.assert_called_once()
        sess.flush.assert_called_once()

    async def test_returns_existing_workflow(self):
        from backend.stores.workflow import WorkflowStore

        existing = WorkflowInstance(store_id=1, current_state=WorkflowState.DIAGNOSIS.value)
        sess = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=existing)
        sess.execute.return_value = mock_result

        store = WorkflowStore(sess)
        wf = await store.get_or_create_workflow(store_id=1)

        assert wf is existing
        sess.add.assert_not_called()


class TestTransitionWorkflow:
    async def test_updates_state_and_flushes(self):
        from backend.stores.workflow import WorkflowStore

        sess = _make_session()
        wf = WorkflowInstance(store_id=1, current_state=WorkflowState.DIAGNOSIS.value)

        store = WorkflowStore(sess)
        await store.transition_workflow(wf, WorkflowState.DIAGNOSIS, WorkflowState.FOUNDATION)

        assert wf.current_state == WorkflowState.FOUNDATION.value
        sess.add.assert_called()
        sess.flush.assert_called()

    async def test_invalid_transition_returns_early(self):
        from backend.stores.workflow import WorkflowStore

        sess = _make_session()
        wf = WorkflowInstance(store_id=1, current_state=WorkflowState.DIAGNOSIS.value)

        store = WorkflowStore(sess)
        await store.transition_workflow(wf, WorkflowState.DIAGNOSIS, WorkflowState.DAILY_OPS)

        # State should not change for invalid transition
        assert wf.current_state == WorkflowState.DIAGNOSIS.value
        sess.add.assert_not_called()


class TestTriggerManualTakeover:
    async def test_sets_manual_review_state(self):
        from backend.stores.workflow import WorkflowStore

        wf = WorkflowInstance(store_id=1, current_state=WorkflowState.DAILY_OPS.value, consecutive_failures=3)
        sess = _make_session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=wf)
        sess.execute.return_value = mock_result

        store = WorkflowStore(sess)
        result = await store.trigger_manual_takeover(wf)

        assert result.current_state == WorkflowState.MANUAL_REVIEW.value
        assert result.consecutive_failures == 0
```

- [ ] **Step 2: 更新 `backend/stores/workflow.py`**

在 `WorkflowStore` 中追加新方法：

```python
    async def create_workflow(self, store_id: int) -> WorkflowInstance:
        """Create a new workflow instance for a store."""
        wf = WorkflowInstance(
            store_id=store_id,
            current_state=WorkflowState.NEW_STORE.value,
            consecutive_failures=0,
            retry_count=0,
            started_at=datetime.now(UTC),
        )
        self._session.add(wf)
        await self._session.flush()
        return wf

    async def get_or_create_workflow(self, store_id: int) -> WorkflowInstance:
        """Get existing workflow or create a new one."""
        wf = await self.get_by_store_id(store_id)
        if wf is None:
            wf = await self.create_workflow(store_id)
        return wf

    async def transition_workflow(
        self,
        wf: WorkflowInstance,
        from_state: WorkflowState,
        to_state: WorkflowState,
    ) -> None:
        """Transition workflow to a new state with validation."""
        valid = VALID_TRANSITIONS.get(from_state, set())
        if to_state not in valid:
            logger.error(f"Invalid transition: {from_state.value} -> {to_state.value}")
            return

        wf.current_state = to_state.value
        self._session.add(wf)
        await self._session.flush()
        logger.info(f"Store {wf.store_id}: transitioned {from_state.value} -> {to_state.value}")

    async def trigger_manual_takeover(self, wf: WorkflowInstance) -> WorkflowInstance:
        """Move a workflow to MANUAL_REVIEW state."""
        wf.current_state = WorkflowState.MANUAL_REVIEW.value
        wf.consecutive_failures = 0
        wf.updated_at = datetime.now(UTC)
        self._session.add(wf)
        await self._session.flush()
        logger.info(f"Manual takeover triggered for store {wf.store_id}")
        return wf

    async def update_timestamp(self, wf: WorkflowInstance) -> None:
        """Update workflow updated_at timestamp."""
        wf.updated_at = datetime.now(UTC)
        self._session.add(wf)
        await self._session.flush()
```

同时在文件顶部添加缺失的导入：

```python
from datetime import UTC, datetime
from backend.models import VALID_TRANSITIONS, WorkflowInstance, WorkflowState
```

- [ ] **Step 3: 运行测试和 ruff**
```bash
pytest tests/test_workflow_store.py -v
ruff check backend/stores/workflow.py tests/test_workflow_store.py
```

- [ ] **Step 4: 提交**
```bash
git add backend/stores/workflow.py tests/test_workflow_store.py
git commit -m "feat(stores): add workflow lifecycle methods"
```

---

## Task 2: 扩展 AgentRunStore

**Files:**
- Modify: `backend/stores/agent_run.py`
- Test: `tests/test_agent_run_store.py` (新建)

- [ ] **Step 1: 创建 `tests/test_agent_run_store.py`**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.models import AgentRun


def _make_session():
    sess = MagicMock()
    sess.add = MagicMock()
    sess.flush = AsyncMock()
    return sess


@pytest.mark.asyncio
class TestCreateAgentRun:
    async def test_creates_agent_run_with_all_fields(self):
        from backend.stores.agent_run import AgentRunStore

        sess = _make_session()
        store = AgentRunStore(sess)

        result = await store.create_agent_run(
            store_id=1,
            agent_type="analyzer",
            status="success",
            state_at_run="DIAGNOSIS",
            input_data={"store_data": {}},
            output_data={"result": "ok"},
            error_msg=None,
            retry_count=0,
            duration_ms=150,
        )

        sess.add.assert_called_once()
        sess.flush.assert_called_once()
        added: AgentRun = sess.add.call_args[0][0]
        assert added.store_id == 1
        assert added.agent_type == "analyzer"
        assert added.status == "success"
        assert added.state_at_run == "DIAGNOSIS"
        assert added.retry_count == 0
        assert added.duration_ms == 150
```

- [ ] **Step 2: 更新 `backend/stores/agent_run.py`**

在 `AgentRunStore` 中追加：

```python
    async def create_agent_run(
        self,
        store_id: int,
        agent_type: str,
        status: str,
        state_at_run: str,
        input_data: dict,
        output_data: dict,
        error_msg: str | None,
        retry_count: int,
        duration_ms: int,
    ) -> AgentRun:
        """Create and persist an agent run record."""
        run = AgentRun(
            store_id=store_id,
            agent_type=agent_type,
            status=status,
            state_at_run=state_at_run,
            input_data=input_data,
            output_data=output_data,
            error_msg=error_msg,
            retry_count=retry_count,
            duration_ms=duration_ms,
        )
        self._session.add(run)
        await self._session.flush()
        return run
```

- [ ] **Step 3: 运行测试和 ruff**
```bash
pytest tests/test_agent_run_store.py -v
ruff check backend/stores/agent_run.py tests/test_agent_run_store.py
```

- [ ] **Step 4: 提交**
```bash
git add backend/stores/agent_run.py tests/test_agent_run_store.py
git commit -m "feat(stores): add AgentRunStore.create_agent_run"
```

---

## Task 3: 新建 ReportStore

**Files:**
- Create: `backend/stores/report.py`
- Test: `tests/test_report_store.py` (新建)

- [ ] **Step 1: 创建 `backend/stores/report.py`**

```python
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Report


class ReportStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_report(
        self,
        store_id: int,
        report_type: str,
        content_md: str | None,
        content_json: dict | None,
    ) -> Report:
        """Create and persist a report record."""
        report = Report(
            store_id=store_id,
            report_type=report_type,
            content_md=content_md,
            content_json=content_json or {},
        )
        self._session.add(report)
        await self._session.flush()
        return report
```

- [ ] **Step 2: 创建 `tests/test_report_store.py`**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.models import Report


def _make_session():
    sess = MagicMock()
    sess.add = MagicMock()
    sess.flush = AsyncMock()
    return sess


@pytest.mark.asyncio
class TestCreateReport:
    async def test_creates_report_with_all_fields(self):
        from backend.stores.report import ReportStore

        sess = _make_session()
        store = ReportStore(sess)

        result = await store.create_report(
            store_id=1,
            report_type="weekly",
            content_md="# Weekly Report\n...",
            content_json={"metrics": {"gmv": 5000}},
        )

        sess.add.assert_called_once()
        sess.flush.assert_called_once()
        added: Report = sess.add.call_args[0][0]
        assert added.store_id == 1
        assert added.report_type == "weekly"
        assert added.content_md == "# Weekly Report\n..."
        assert added.content_json == {"metrics": {"gmv": 5000}}

    async def test_defaults_content_json_to_empty_dict(self):
        from backend.stores.report import ReportStore

        sess = _make_session()
        store = ReportStore(sess)

        result = await store.create_report(
            store_id=2,
            report_type="daily",
            content_md="# Daily",
            content_json=None,
        )

        added: Report = sess.add.call_args[0][0]
        assert added.content_json == {}
```

- [ ] **Step 3: 更新 `backend/stores/__init__.py`**

```python
from backend.stores.agent_run import AgentRunStore
from backend.stores.alert import AlertStore
from backend.stores.event_log import EventLogStore
from backend.stores.report import ReportStore
from backend.stores.store import StoreStore
from backend.stores.workflow import WorkflowStore

__all__ = [
    "AgentRunStore",
    "AlertStore",
    "EventLogStore",
    "ReportStore",
    "StoreStore",
    "WorkflowStore",
]
```

- [ ] **Step 4: 运行测试和 ruff**
```bash
pytest tests/test_report_store.py -v
ruff check backend/stores/report.py backend/stores/__init__.py tests/test_report_store.py
```

- [ ] **Step 5: 提交**
```bash
git add backend/stores/report.py backend/stores/__init__.py tests/test_report_store.py
git commit -m "feat(stores): add ReportStore"
```

---

## Task 4: 重构 StateMachine（移除 DB 方法）

**Files:**
- Modify: `backend/orchestrator/state_machine.py`
- Modify: `tests/test_state_machine.py` (删除已迁移的 async 测试)

- [ ] **Step 1: 重写 `backend/orchestrator/state_machine.py`**

删除所有 async 方法，只保留纯函数：

```python
from __future__ import annotations

from backend.models import VALID_TRANSITIONS, WorkflowState


class StateMachine:
    """
    Pure stateless state transition logic.
    """

    STATES_REQUIRING_ANALYZER = {WorkflowState.DIAGNOSIS}
    STATES_REQUIRING_WEB_OPS = {WorkflowState.FOUNDATION, WorkflowState.DAILY_OPS}
    STATES_REQUIRING_MOBILE_OPS = {WorkflowState.DAILY_OPS}
    STATES_REQUIRING_REPORTER = {WorkflowState.WEEKLY_REPORT}

    def get_agents_for_state(self, state: WorkflowState) -> list[str]:
        agents: list[str] = []
        if state in self.STATES_REQUIRING_ANALYZER:
            agents.append("analyzer")
        if state in self.STATES_REQUIRING_WEB_OPS:
            agents.append("web_operator")
        if state in self.STATES_REQUIRING_MOBILE_OPS:
            agents.append("mobile_operator")
        if state in self.STATES_REQUIRING_REPORTER:
            agents.append("reporter")
        return agents

    def get_next_state(self, current: WorkflowState) -> WorkflowState:
        next_map: dict[WorkflowState, WorkflowState] = {
            WorkflowState.NEW_STORE: WorkflowState.DIAGNOSIS,
            WorkflowState.DIAGNOSIS: WorkflowState.FOUNDATION,
            WorkflowState.FOUNDATION: WorkflowState.DAILY_OPS,
            WorkflowState.DAILY_OPS: WorkflowState.WEEKLY_REPORT,
            WorkflowState.WEEKLY_REPORT: WorkflowState.DONE,
        }
        return next_map.get(current, current)

    def is_valid_transition(self, from_: WorkflowState, to: WorkflowState) -> bool:
        return to in VALID_TRANSITIONS.get(from_, set())
```

- [ ] **Step 2: 更新 `tests/test_state_machine.py`**

删除 `TestGetOrCreateWorkflow` 和 `TestTriggerManualTakeover` 两个 async 测试类（已迁移到 `test_workflow_store.py`）。保留 `TestGetAgentsForState`、`TestGetNextState`、`TestIsValidTransition`。

- [ ] **Step 3: 运行测试和 ruff**
```bash
pytest tests/test_state_machine.py -v
ruff check backend/orchestrator/state_machine.py tests/test_state_machine.py
```

- [ ] **Step 4: 提交**
```bash
git add backend/orchestrator/state_machine.py tests/test_state_machine.py
git commit -m "refactor(orchestrator): StateMachine becomes pure stateless class"
```

---

## Task 5: 重构 EventEmitter（接收 model 实例）

**Files:**
- Modify: `backend/orchestrator/event_emitter.py`
- Test: `tests/test_event_emitter.py` (更新)

- [ ] **Step 1: 重写 `backend/orchestrator/event_emitter.py`**

```python
from __future__ import annotations

from backend.models import Alert, EventLog


class EventEmitter:
    """
    Thin wrapper that persists EventLog and Alert model instances.
    """

    def __init__(self, db) -> None:
        self._db = db

    def emit_event(self, event: EventLog) -> None:
        """Persist an event log entry."""
        self._db.add(event)

    def emit_alert(self, alert: Alert) -> None:
        """Persist an alert entry."""
        self._db.add(alert)
```

- [ ] **Step 2: 更新 `tests/test_event_emitter.py`**

```python
import pytest
from unittest.mock import MagicMock

from backend.models import Alert, EventLog
from backend.orchestrator.event_emitter import EventEmitter


class TestEmitEvent:
    def test_adds_event_to_session(self):
        mock_db = MagicMock()

        emitter = EventEmitter(mock_db)
        event = EventLog(
            store_id=1,
            event_type="agent_run",
            from_state="DIAGNOSIS",
            to_state="DIAGNOSIS",
            agent_type="analyzer",
            message="analyzer success (150ms)",
            extra_data={"run_id": 5, "error": None},
        )

        emitter.emit_event(event)

        mock_db.add.assert_called_once_with(event)

    def test_adds_minimal_event(self):
        mock_db = MagicMock()

        emitter = EventEmitter(mock_db)
        event = EventLog(store_id=2, event_type="workflow_created")

        emitter.emit_event(event)

        mock_db.add.assert_called_once_with(event)


class TestEmitAlert:
    def test_adds_alert_to_session(self):
        mock_db = MagicMock()

        emitter = EventEmitter(mock_db)
        alert = Alert(
            store_id=1,
            alert_type="consecutive_failure",
            severity="critical",
            message="连续3次失败",
            extra_data={"failures": 3},
        )

        emitter.emit_alert(alert)

        mock_db.add.assert_called_once_with(alert)

    def test_adds_warning_alert(self):
        mock_db = MagicMock()

        emitter = EventEmitter(mock_db)
        alert = Alert(
            store_id=2,
            alert_type="manual_takeover",
            severity="warning",
            message="人工接管已触发",
        )

        emitter.emit_alert(alert)

        mock_db.add.assert_called_once_with(alert)
```

- [ ] **Step 3: 运行测试和 ruff**
```bash
pytest tests/test_event_emitter.py -v
ruff check backend/orchestrator/event_emitter.py tests/test_event_emitter.py
```

- [ ] **Step 4: 提交**
```bash
git add backend/orchestrator/event_emitter.py tests/test_event_emitter.py
git commit -m "refactor(orchestrator): EventEmitter receives model instances"
```

---

## Task 6: 重构 WorkflowEngine（使用 stores，移除 db.add）

**Files:**
- Modify: `backend/orchestrator/engine.py`

- [ ] **Step 1: 重写 `backend/orchestrator/engine.py`**

```python
from __future__ import annotations

from backend.agents.base import AgentResult, AgentResultStatus
from backend.logging_config import get_logger
from backend.models import AgentRun, Alert, EventLog, Report, Store, WorkflowInstance, WorkflowState
from backend.orchestrator.agent_runner import AgentRunner
from backend.orchestrator.event_emitter import EventEmitter
from backend.orchestrator.state_machine import StateMachine
from backend.stores.agent_run import AgentRunStore
from backend.stores.report import ReportStore
from backend.stores.workflow import WorkflowStore

logger = get_logger(__name__)


class WorkflowEngine:
    """
    Orchestrates the multi-agent workflow for a single store.
    Entry point that coordinates StateMachine, EventEmitter, AgentRunner, and stores.
    """

    MAX_RETRIES = 3

    def __init__(
        self,
        workflow_store: WorkflowStore,
        agent_run_store: AgentRunStore,
        report_store: ReportStore,
        state_machine: StateMachine,
        event_emitter: EventEmitter,
        agent_runner: AgentRunner,
    ) -> None:
        self._wf = workflow_store
        self._agent_run = agent_run_store
        self._report = report_store
        self.sm = state_machine
        self.emitter = event_emitter
        self.runner = agent_runner

    async def get_or_create_workflow(self, store: Store) -> WorkflowInstance:
        return await self._wf.get_or_create_workflow(store.id)

    async def run_workflow(self, store: Store) -> WorkflowInstance:
        wf = await self._wf.get_or_create_workflow(store.id)
        state = WorkflowState(wf.current_state)

        logger.info(f"Starting workflow for store {store.store_id}, state={state.value}")

        if state == WorkflowState.DONE:
            logger.info("Store already DONE, skipping")
            return wf

        agents_to_run = self.sm.get_agents_for_state(state)

        context: dict = {
            "store_id": store.store_id,
            "store_data": self.runner.store_to_dict(store),
            "workflow_state": state.value,
        }

        any_failure = False

        for agent_type in agents_to_run:
            context, result = await self.runner.run(
                agent_type, context, max_retries=self.MAX_RETRIES
            )
            await self._persist_agent_run(store.id, agent_type, context, result, state)

            if result.status != AgentResultStatus.SUCCESS:
                any_failure = True
                break

        if any_failure:
            wf.consecutive_failures += 1
            if wf.consecutive_failures >= self.MAX_RETRIES:
                next_state = WorkflowState.MANUAL_REVIEW
                alert = Alert(
                    store_id=store.id,
                    alert_type="consecutive_failure",
                    severity="critical",
                    message=f"连续{self.MAX_RETRIES}次失败，触发人工接管",
                    extra_data={"failures": wf.consecutive_failures},
                )
                self.emitter.emit_alert(alert)
                logger.warning(
                    f"Store {store.store_id}: consecutive failures "
                    f"{wf.consecutive_failures} -> MANUAL_REVIEW"
                )
            else:
                next_state = state
                logger.warning(
                    f"Store {store.store_id}: failure in {state.value}, "
                    f"retry {wf.consecutive_failures}/{self.MAX_RETRIES - 1}"
                )
        else:
            wf.consecutive_failures = 0
            next_state = self.sm.get_next_state(state)
            logger.info(
                f"Store {store.store_id}: {state.value} completed, "
                f"transitioning to {next_state.value}"
            )

        if next_state != state:
            await self._wf.transition_workflow(wf, state, next_state)
            event = EventLog(
                store_id=store.id,
                event_type="state_change",
                from_state=state.value,
                to_state=next_state.value,
                message=f"State transition: {state.value} -> {next_state.value}",
            )
            self.emitter.emit_event(event)

        if next_state == WorkflowState.WEEKLY_REPORT:
            await self._generate_report(store, context, "weekly")

        await self._wf.update_timestamp(wf)
        return wf

    async def _persist_agent_run(
        self,
        store_id: int,
        agent_type: str,
        context: dict,
        result: AgentResult,
        state: WorkflowState,
    ) -> None:
        retry_count = getattr(result, "attempts", 1) - 1

        run = await self._agent_run.create_agent_run(
            store_id=store_id,
            agent_type=agent_type,
            status=result.status.value,
            state_at_run=state.value,
            input_data={"store_data": context.get("store_data", {})},
            output_data=result.data or {},
            error_msg=result.error,
            retry_count=retry_count,
            duration_ms=result.duration_ms,
        )

        event = EventLog(
            store_id=store_id,
            event_type="agent_run",
            agent_type=agent_type,
            message=f"{agent_type} {result.status.value} ({result.duration_ms}ms)",
            extra_data={"run_id": run.id, "error": result.error},
        )
        self.emitter.emit_event(event)

    async def _generate_report(self, store: Store, context: dict, report_type: str) -> None:
        report_context: dict = {
            **context,
            "store_id": store.store_id,
            "store_data": self.runner.store_to_dict(store),
            "report_type": report_type,
        }

        _, result = await self.runner.run("reporter", report_context)

        if result.status == AgentResultStatus.SUCCESS:
            report = await self._report.create_report(
                store_id=store.id,
                report_type=report_type,
                content_md=result.data.get("md_report"),
                content_json=result.data.get("json_report"),
            )
            event = EventLog(
                store_id=store.id,
                event_type="report_generated",
                message=f"{report_type} report generated",
                extra_data={"report_id": report.id},
            )
            self.emitter.emit_event(event)
            logger.info(f"Report generated for store {store.store_id}")

    async def trigger_manual_takeover(self, store: Store) -> WorkflowInstance:
        wf = await self._wf.get_or_create_workflow(store.id)
        old_state = WorkflowState(wf.current_state)

        await self._wf.trigger_manual_takeover(wf)

        self.emitter.emit_event(EventLog(
            store_id=store.id,
            event_type="manual_takeover",
            from_state=old_state.value,
            to_state=WorkflowState.MANUAL_REVIEW.value,
            message="Manual takeover triggered",
        ))
        self.emitter.emit_alert(Alert(
            store_id=store.id,
            alert_type="manual_takeover",
            severity="warning",
            message="人工接管已触发",
        ))
        logger.info(f"Manual takeover triggered for store {store.store_id}")
        return wf
```

- [ ] **Step 2: 运行 ruff**
```bash
ruff check backend/orchestrator/engine.py
```

- [ ] **Step 3: 提交**
```bash
git add backend/orchestrator/engine.py
git commit -m "refactor(orchestrator): Engine delegates all DB ops to stores"
```

---

## Task 7: 更新 WorkflowService 和路由注入

**Files:**
- Modify: `backend/service/workflow.py`
- Modify: `backend/routes/workflows.py`

- [ ] **Step 1: 更新 `backend/service/workflow.py`**

```python
# 在 __init__ 中替换 state_machine 注入为 workflow_store
# 更新 start_workflow 和 manual_takeover 中的 Engine 构造

# 替换 __init__ 中的 state_machine 参数：
        workflow_store: WorkflowStore,
        agent_run_store: AgentRunStore,
        event_log_store: EventLogStore,
        report_store: ReportStore,
        state_machine: StateMachine,
        event_emitter: EventEmitter,
        agent_runner: AgentRunner,

# start_workflow 中的 Engine 构造改为：
eng = WorkflowEngine(
    workflow_store=self._workflow,
    agent_run_store=self._agent_run,
    report_store=report_store,
    state_machine=self._state_machine,
    event_emitter=self._event_emitter,
    agent_runner=self._agent_runner,
)

# manual_takeover 同理
```

- [ ] **Step 2: 更新 `backend/routes/workflows.py`**

在 `_build_workflow_service` 中添加 `ReportStore` 实例化：

```python
from backend.stores.report import ReportStore

def _build_workflow_service(...) -> WorkflowService:
    report_store = ReportStore(db)
    return WorkflowService(
        db,
        store_store,
        workflow_store,
        agent_run_store,
        event_log_store,
        report_store,
        StateMachine(),
        EventEmitter(db),
        AgentRunner(agents),
    )
```

同时在所有 endpoint 中添加 `EventEmitter(db)` 的创建（因为 `EventEmitter` 现在持有 `db`）：

```python
def _build_workflow_service(...) -> WorkflowService:
    return WorkflowService(
        db,
        store_store,
        workflow_store,
        agent_run_store,
        event_log_store,
        ReportStore(db),
        StateMachine(),
        EventEmitter(db),
        AgentRunner(agents),
    )
```

- [ ] **Step 3: 运行 ruff**
```bash
ruff check backend/service/workflow.py backend/routes/workflows.py
```

- [ ] **Step 4: 提交**
```bash
git add backend/service/workflow.py backend/routes/workflows.py
git commit -m "refactor(service): wire ReportStore into orchestrator DI"
```

---

## Task 8: 更新集成测试

**Files:**
- Modify: `tests/test_orchestrator_engine.py`

- [ ] **Step 1: 更新 `test_orchestrator_engine.py`**

重构 `_make_emitter` 函数以适配新的 `emit_event`/`emit_alert` API：

```python
def _make_emitter():
    emitter = MagicMock()
    emitter.emit_event = MagicMock()
    emitter.emit_alert = MagicMock()
    return emitter
```

重构 `_make_sm` 以适配新的 store-based API：

```python
def _make_wf_store(initial_state: WorkflowState = WorkflowState.NEW_STORE):
    wf = MagicMock()
    wf.current_state = initial_state.value
    wf.consecutive_failures = 0
    wf.store_id = 1

    wf_store = MagicMock()
    wf_store.get_or_create_workflow = AsyncMock(return_value=wf)
    wf_store.transition_workflow = AsyncMock()
    wf_store.trigger_manual_takeover = AsyncMock(return_value=wf)
    wf_store.update_timestamp = AsyncMock()
    return wf_store, wf


def _make_agent_run_store():
    ar_store = MagicMock()
    run = MagicMock()
    run.id = 5
    ar_store.create_agent_run = AsyncMock(return_value=run)
    return ar_store


def _make_report_store():
    rp_store = MagicMock()
    report = MagicMock()
    report.id = 10
    rp_store.create_report = AsyncMock(return_value=report)
    return rp_store
```

更新所有测试方法，将 `sm`、`emitter` 替换为新的 store-based mocks：

```python
async def test_engine_calls_runner_for_each_agent(self):
    wf_store, wf = _make_wf_store(WorkflowState.DAILY_OPS)
    ar_store = _make_agent_run_store()
    rp_store = _make_report_store()

    sm = MagicMock()
    sm.get_agents_for_state = MagicMock(return_value=["web_operator", "mobile_operator"])

    results = {
        "web_operator": AgentResult(agent_type="web_operator", status=AgentResultStatus.SUCCESS),
        "mobile_operator": AgentResult(agent_type="mobile_operator", status=AgentResultStatus.SUCCESS),
    }
    runner = _make_runner(results)
    emitter = _make_emitter()

    engine = WorkflowEngine(
        workflow_store=wf_store,
        agent_run_store=ar_store,
        report_store=rp_store,
        state_machine=sm,
        event_emitter=emitter,
        agent_runner=runner,
    )
    store = MagicMock()
    store.id = 1
    store.store_id = "test"

    await engine.run_workflow(store)

    assert runner.run.call_count == 2
```

注意：`test_engine_transitions_on_success` 测试中，`sm.get_next_state` 应返回 `FOUNDATION`，并验证 `wf_store.transition_workflow` 被调用：

```python
    async def test_engine_transitions_on_success(self):
        wf_store, wf = _make_wf_store(WorkflowState.DIAGNOSIS)
        wf_store.transition_workflow = AsyncMock()
        ar_store = _make_agent_run_store()
        rp_store = _make_report_store()

        sm = MagicMock()
        sm.get_agents_for_state = MagicMock(return_value=["analyzer"])
        sm.get_next_state = MagicMock(return_value=WorkflowState.FOUNDATION)

        runner = _make_runner({"analyzer": AgentResult(agent_type="analyzer", status=AgentResultStatus.SUCCESS)})
        emitter = _make_emitter()

        engine = WorkflowEngine(
            workflow_store=wf_store,
            agent_run_store=ar_store,
            report_store=rp_store,
            state_machine=sm,
            event_emitter=emitter,
            agent_runner=runner,
        )
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        await engine.run_workflow(store)

        wf_store.transition_workflow.assert_called_once()
        transition_call = wf_store.transition_workflow.call_args
        assert transition_call[0][1] == WorkflowState.DIAGNOSIS
        assert transition_call[0][2] == WorkflowState.FOUNDATION
```

同样更新其他测试方法。共需更新 7 个测试。

- [ ] **Step 2: 运行测试和 ruff**
```bash
pytest tests/test_orchestrator_engine.py -v
ruff check tests/test_orchestrator_engine.py
```

- [ ] **Step 3: 提交**
```bash
git add tests/test_orchestrator_engine.py
git commit -m "test(engine): update mocks for store-based DI"
```

---

## Task 9: 全量验证

- [ ] **Step 1: 运行完整测试套件**
```bash
pytest tests/ -v
```
Expected: ALL PASS

- [ ] **Step 2: 运行 ruff 检查全部 backend 代码**
```bash
ruff check backend/
```
Expected: no errors

- [ ] **Step 3: 验证行数精简效果**
```bash
wc -l backend/orchestrator/state_machine.py backend/orchestrator/engine.py
```
Expected: `state_machine.py` ~55行（纯函数），`engine.py` ~145行（纯编排）

- [ ] **Step 4: 确认 db 参数已消除**
```bash
grep -n "self.db" backend/orchestrator/engine.py
grep -n "db.add\|db.flush" backend/orchestrator/engine.py
grep -n "AsyncSession" backend/orchestrator/engine.py
```
Expected: 0 matches

- [ ] **Step 5: 提交最终状态**
```bash
git add -A && git commit -m "refactor(orchestrator): eliminate direct DB access — all ops via stores"
```

---

## 自检清单

- [ ] `state_machine.py` 无 `AsyncSession` 导入，无 `db.add`/`db.flush`
- [ ] `engine.py` 无 `AsyncSession` 导入，无 `self.db`，无 `db.add`/`db.flush`
- [ ] `event_emitter.py` 仅做 `db.add`，无 model 构造逻辑
- [ ] `workflow.py` (store) 持有所有 workflow DB 操作
- [ ] `agent_run.py` (store) 持有 `create_agent_run`
- [ ] `report.py` (store) 新建，持有 `create_report`
- [ ] `__init__.py` (stores) 导出 `ReportStore`
- [ ] `workflow.py` (service) 添加 `report_store` 注入
- [ ] `workflows.py` (routes) 传入 `ReportStore(db)` 和 `EventEmitter(db)`
- [ ] 所有旧 async 测试已从 `test_state_machine.py` 移除
- [ ] `test_orchestrator_engine.py` 全部 7 个测试通过
- [ ] `make backend-test` 全部通过
- [ ] `ruff check backend/` 无错误
