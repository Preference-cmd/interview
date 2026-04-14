# Orchestrator 重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `backend/orchestrator/engine.py` (384行) 拆解为 StateMachine + EventEmitter + AgentRunner + WorkflowEngine 组合结构，通过依赖注入传递 Agent 实例，各组件独立测试。

**Architecture:** Composition 模式 — WorkflowEngine 作为唯一入口，持有 StateMachine、EventEmitter、AgentRunner 三个组件，各司其职。Agent 实例由外部构造并注入 AgentRunner。

**Tech Stack:** Python 3.12 + pytest-asyncio + unittest.mock + Ruff

---

## 文件变更总览

| 操作 | 文件 |
|------|------|
| 新建 | `backend/orchestrator/state_machine.py` |
| 新建 | `backend/orchestrator/event_emitter.py` |
| 新建 | `backend/orchestrator/agent_runner.py` |
| 修改 | `backend/orchestrator/engine.py` (精简至 ~80 行) |
| 修改 | `backend/orchestrator/__init__.py` (导出新增类) |
| 修改 | `backend/routes/workflows.py` (适配 DI) |
| 新建 | `tests/test_state_machine.py` |
| 新建 | `tests/test_event_emitter.py` |
| 新建 | `tests/test_agent_runner.py` |
| 新建 | `tests/test_orchestrator_engine.py` |
| 删除 | `tests/test_example.py` (迁移至新文件) |

**依赖关系：** Task 1-3 可并行；Task 4 依赖 1-3；Task 5-6 依赖 4；Task 7 依赖全部。

---

## Task 1: StateMachine 组件

**Files:**
- Create: `backend/orchestrator/state_machine.py`
- Test: `tests/test_state_machine.py`

### 子任务 1a: 创建 StateMachine 类骨架

- [ ] **Step 1: 创建 `backend/orchestrator/state_machine.py`**

```python
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.logging_config import get_logger
from backend.models import (
    VALID_TRANSITIONS,
    Store,
    WorkflowInstance,
    WorkflowState,
)

logger = get_logger(__name__)


class StateMachine:
    """
    Manages workflow state transitions and agent-to-state mappings.
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

- [ ] **Step 2: 提交**
```bash
git add backend/orchestrator/state_machine.py
git commit -m "feat(orchestrator): add StateMachine component"
```

### 子任务 1b: 添加 DB 相关方法

- [ ] **Step 1: 在 `state_machine.py` 末尾追加 `get_or_create_workflow`**

```python
    async def get_or_create_workflow(
        self, db: AsyncSession, store: Store
    ) -> WorkflowInstance:
        """Get existing workflow or create a new one for the store."""
        stmt = select(WorkflowInstance).where(WorkflowInstance.store_id == store.id)
        result = await db.execute(stmt)
        wf = result.scalar_one_or_none()
        if wf is None:
            wf = WorkflowInstance(
                store_id=store.id,
                current_state=WorkflowState.NEW_STORE.value,
                consecutive_failures=0,
                retry_count=0,
                started_at=datetime.now(UTC),
            )
            db.add(wf)
            await db.flush()
            logger.info(f"Created workflow for store {store.store_id}")
        return wf

    async def transition(
        self,
        db: AsyncSession,
        store_id: int,
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
        db.add(wf)
        await db.flush()
        logger.info(f"Store {store_id}: transitioned {from_state.value} -> {to_state.value}")

    async def trigger_manual_takeover(
        self, db: AsyncSession, store: Store
    ) -> WorkflowInstance:
        """Move a store to MANUAL_REVIEW state."""
        wf = await self.get_or_create_workflow(db, store)
        old_state = WorkflowState(wf.current_state)

        wf.current_state = WorkflowState.MANUAL_REVIEW.value
        wf.consecutive_failures = 0
        wf.updated_at = datetime.now(UTC)
        db.add(wf)
        await db.flush()

        logger.info(f"Manual takeover triggered for store {store.store_id}")
        return wf
```

- [ ] **Step 2: 提交**
```bash
git add backend/orchestrator/state_machine.py
git commit -m "feat(orchestrator): add StateMachine DB methods"
```

### 子任务 1c: 编写 StateMachine 测试

- [ ] **Step 1: 创建 `tests/test_state_machine.py`**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.models._enums import WorkflowState
from backend.orchestrator.state_machine import StateMachine


class TestGetAgentsForState:
    def setup_method(self):
        self.sm = StateMachine()

    def test_diagnosis_runs_analyzer(self):
        agents = self.sm.get_agents_for_state(WorkflowState.DIAGNOSIS)
        assert agents == ["analyzer"]

    def test_daily_ops_runs_web_and_mobile(self):
        agents = self.sm.get_agents_for_state(WorkflowState.DAILY_OPS)
        assert agents == ["web_operator", "mobile_operator"]

    def test_weekly_report_runs_reporter(self):
        agents = self.sm.get_agents_for_state(WorkflowState.WEEKLY_REPORT)
        assert agents == ["reporter"]

    def test_daily_ops_includes_web_operator(self):
        agents = self.sm.get_agents_for_state(WorkflowState.DAILY_OPS)
        assert "web_operator" in agents

    def test_daily_ops_includes_mobile_operator(self):
        agents = self.sm.get_agents_for_state(WorkflowState.DAILY_OPS)
        assert "mobile_operator" in agents

    def test_new_store_runs_no_agents(self):
        agents = self.sm.get_agents_for_state(WorkflowState.NEW_STORE)
        assert agents == []

    def test_manual_review_runs_no_agents(self):
        agents = self.sm.get_agents_for_state(WorkflowState.MANUAL_REVIEW)
        assert agents == []

    def test_done_runs_no_agents(self):
        agents = self.sm.get_agents_for_state(WorkflowState.DONE)
        assert agents == []


class TestGetNextState:
    def setup_method(self):
        self.sm = StateMachine()

    def test_new_store_to_diagnosis(self):
        assert self.sm.get_next_state(WorkflowState.NEW_STORE) == WorkflowState.DIAGNOSIS

    def test_diagnosis_to_foundation(self):
        assert self.sm.get_next_state(WorkflowState.DIAGNOSIS) == WorkflowState.FOUNDATION

    def test_foundation_to_daily_ops(self):
        assert self.sm.get_next_state(WorkflowState.FOUNDATION) == WorkflowState.DAILY_OPS

    def test_daily_ops_to_weekly_report(self):
        assert self.sm.get_next_state(WorkflowState.DAILY_OPS) == WorkflowState.WEEKLY_REPORT

    def test_weekly_report_to_done(self):
        assert self.sm.get_next_state(WorkflowState.WEEKLY_REPORT) == WorkflowState.DONE

    def test_done_stays_done(self):
        assert self.sm.get_next_state(WorkflowState.DONE) == WorkflowState.DONE

    def test_manual_review_stays_same(self):
        assert self.sm.get_next_state(WorkflowState.MANUAL_REVIEW) == WorkflowState.MANUAL_REVIEW


class TestIsValidTransition:
    def setup_method(self):
        self.sm = StateMachine()

    def test_new_store_to_diagnosis_valid(self):
        assert self.sm.is_valid_transition(WorkflowState.NEW_STORE, WorkflowState.DIAGNOSIS) is True

    def test_new_store_to_manual_review_valid(self):
        assert self.sm.is_valid_transition(WorkflowState.NEW_STORE, WorkflowState.MANUAL_REVIEW) is True

    def test_diagnosis_to_foundation_valid(self):
        assert self.sm.is_valid_transition(WorkflowState.DIAGNOSIS, WorkflowState.FOUNDATION) is True

    def test_diagnosis_to_daily_ops_invalid(self):
        assert self.sm.is_valid_transition(WorkflowState.DIAGNOSIS, WorkflowState.DAILY_OPS) is False

    def test_done_has_no_valid_transitions(self):
        for state in WorkflowState:
            assert self.sm.is_valid_transition(WorkflowState.DONE, state) is False


@pytest.mark.asyncio
class TestGetOrCreateWorkflow:
    async def test_creates_new_workflow(self):
        from backend.models import Store, WorkflowState

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute.return_value = mock_result

        store = MagicMock(spec=Store)
        store.id = 1
        store.store_id = "test_001"

        sm = StateMachine()
        wf = await sm.get_or_create_workflow(mock_db, store)

        assert wf.current_state == WorkflowState.NEW_STORE.value
        assert wf.consecutive_failures == 0
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    async def test_returns_existing_workflow(self):
        from backend.models import Store, WorkflowState, WorkflowInstance

        mock_db = AsyncMock()
        existing_wf = WorkflowInstance(
            store_id=1,
            current_state=WorkflowState.DIAGNOSIS.value,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=existing_wf)
        mock_db.execute.return_value = mock_result

        store = MagicMock(spec=Store)
        store.id = 1

        sm = StateMachine()
        wf = await sm.get_or_create_workflow(mock_db, store)

        assert wf is existing_wf
        mock_db.add.assert_not_called()


@pytest.mark.asyncio
class TestTriggerManualTakeover:
    async def test_sets_manual_review_state(self):
        from backend.models import Store, WorkflowState, WorkflowInstance

        existing_wf = WorkflowInstance(
            store_id=1,
            current_state=WorkflowState.DAILY_OPS.value,
            consecutive_failures=2,
        )
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=existing_wf)
        mock_db.execute.return_value = mock_result

        store = MagicMock(spec=Store)
        store.id = 1
        store.store_id = "test_001"

        sm = StateMachine()
        wf = await sm.trigger_manual_takeover(mock_db, store)

        assert wf.current_state == WorkflowState.MANUAL_REVIEW.value
        assert wf.consecutive_failures == 0
        mock_db.add.assert_called()
        mock_db.flush.assert_called()
```

- [ ] **Step 2: 运行测试**
```bash
cd /Users/pref2rence/project/lls/multi-agent-ops && pytest tests/test_state_machine.py -v
```
Expected: PASS (15 tests)

- [ ] **Step 3: 运行 ruff**
```bash
cd /Users/pref2rence/project/lls/multi-agent-ops && ruff check backend/orchestrator/state_machine.py tests/test_state_machine.py
```
Expected: no errors

- [ ] **Step 4: 提交**
```bash
git add backend/orchestrator/state_machine.py tests/test_state_machine.py
git commit -m "test(orchestrator): add StateMachine tests"
```

---

## Task 2: EventEmitter 组件

**Files:**
- Create: `backend/orchestrator/event_emitter.py`
- Test: `tests/test_event_emitter.py`

- [ ] **Step 1: 创建 `backend/orchestrator/event_emitter.py`**

```python
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Alert, EventLog


class EventEmitter:
    """
    Handles event logging and alert creation.
    """

    async def log_event(
        self,
        db: AsyncSession,
        store_id: int,
        event_type: str,
        from_state: str | None = None,
        to_state: str | None = None,
        agent_type: str | None = None,
        message: str | None = None,
        extra_data: dict | None = None,
    ) -> None:
        """Create a structured event log entry."""
        event = EventLog(
            store_id=store_id,
            event_type=event_type,
            from_state=from_state,
            to_state=to_state,
            agent_type=agent_type,
            message=message,
            extra_data=extra_data or {},
        )
        db.add(event)

    async def create_alert(
        self,
        db: AsyncSession,
        store_id: int,
        alert_type: str,
        severity: str,
        message: str,
        extra_data: dict | None = None,
    ) -> None:
        """Create an alert for anomalies."""
        alert = Alert(
            store_id=store_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            extra_data=extra_data or {},
        )
        db.add(alert)
```

- [ ] **Step 2: 提交**
```bash
git add backend/orchestrator/event_emitter.py
git commit -m "feat(orchestrator): add EventEmitter component"
```

- [ ] **Step 3: 创建 `tests/test_event_emitter.py`**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.orchestrator.event_emitter import EventEmitter


@pytest.mark.asyncio
class TestLogEvent:
    async def test_creates_eventlog_with_all_fields(self):
        mock_db = AsyncMock()

        emitter = EventEmitter()
        await emitter.log_event(
            db=mock_db,
            store_id=1,
            event_type="agent_run",
            from_state="DIAGNOSIS",
            to_state="DIAGNOSIS",
            agent_type="analyzer",
            message="analyzer success (150ms)",
            extra_data={"run_id": 5, "error": None},
        )

        mock_db.add.assert_called_once()
        added_event = mock_db.add.call_args[0][0]
        assert added_event.store_id == 1
        assert added_event.event_type == "agent_run"
        assert added_event.from_state == "DIAGNOSIS"
        assert added_event.to_state == "DIAGNOSIS"
        assert added_event.agent_type == "analyzer"
        assert added_event.message == "analyzer success (150ms)"
        assert added_event.extra_data == {"run_id": 5, "error": None}

    async def test_creates_eventlog_with_minimal_fields(self):
        mock_db = AsyncMock()

        emitter = EventEmitter()
        await emitter.log_event(
            db=mock_db,
            store_id=2,
            event_type="workflow_created",
        )

        mock_db.add.assert_called_once()
        added_event = mock_db.add.call_args[0][0]
        assert added_event.store_id == 2
        assert added_event.event_type == "workflow_created"
        assert added_event.from_state is None
        assert added_event.agent_type is None

    async def test_defaults_extra_data_to_empty_dict(self):
        mock_db = AsyncMock()

        emitter = EventEmitter()
        await emitter.log_event(
            db=mock_db,
            store_id=3,
            event_type="state_change",
        )

        added_event = mock_db.add.call_args[0][0]
        assert added_event.extra_data == {}


@pytest.mark.asyncio
class TestCreateAlert:
    async def test_creates_alert_with_all_fields(self):
        mock_db = AsyncMock()

        emitter = EventEmitter()
        await emitter.create_alert(
            db=mock_db,
            store_id=1,
            alert_type="consecutive_failure",
            severity="critical",
            message="连续3次失败，触发人工接管",
            extra_data={"failures": 3},
        )

        mock_db.add.assert_called_once()
        added_alert = mock_db.add.call_args[0][0]
        assert added_alert.store_id == 1
        assert added_alert.alert_type == "consecutive_failure"
        assert added_alert.severity == "critical"
        assert added_alert.message == "连续3次失败，触发人工接管"
        assert added_alert.extra_data == {"failures": 3}

    async def test_defaults_extra_data_to_empty_dict(self):
        mock_db = AsyncMock()

        emitter = EventEmitter()
        await emitter.create_alert(
            db=mock_db,
            store_id=2,
            alert_type="manual_takeover",
            severity="warning",
            message="人工接管已触发",
        )

        added_alert = mock_db.add.call_args[0][0]
        assert added_alert.extra_data == {}
```

- [ ] **Step 4: 运行测试**
```bash
pytest tests/test_event_emitter.py -v
```
Expected: PASS (5 tests)

- [ ] **Step 5: 运行 ruff**
```bash
ruff check backend/orchestrator/event_emitter.py tests/test_event_emitter.py
```
Expected: no errors

- [ ] **Step 6: 提交**
```bash
git add backend/orchestrator/event_emitter.py tests/test_event_emitter.py
git commit -m "test(orchestrator): add EventEmitter tests"
```

---

## Task 3: AgentRunner 组件

**Files:**
- Create: `backend/orchestrator/agent_runner.py`
- Test: `tests/test_agent_runner.py`

- [ ] **Step 1: 创建 `backend/orchestrator/agent_runner.py`**

```python
from __future__ import annotations

from backend.agents.base import AgentResult, AgentResultStatus, BaseAgent
from backend.logging_config import get_logger

logger = get_logger(__name__)


class AgentRunner:
    """
    Executes agents with retry logic and context updates.
    """

    def __init__(self, agents: dict[str, BaseAgent]) -> None:
        self.agents = agents

    async def run(
        self,
        agent_type: str,
        context: dict,
        max_retries: int = 3,
    ) -> tuple[dict, AgentResult]:
        """Run a specific agent, update context, and return result."""
        agent = self.agents.get(agent_type)
        if agent is None:
            result = AgentResult(
                agent_type=agent_type,
                status=AgentResultStatus.FAILED,
                error=f"Unknown agent type: {agent_type}",
            )
            return context, result

        logger.info(f"Running agent {agent_type} for {context.get('store_id')}")

        result = await agent.run_with_retry(context, max_retries=max_retries)

        if result.data:
            context[agent_type] = result.data
            if agent_type == "analyzer":
                context["diagnosis"] = result.data

        return context, result

    def store_to_dict(self, store) -> dict:
        """Convert Store model to dict for agents."""
        return {
            "store_id": store.store_id,
            "name": store.name,
            "city": store.city,
            "category": store.category,
            "rating": store.rating,
            "monthly_orders": store.monthly_orders,
            "gmv_last_7d": store.gmv_last_7d,
            "review_count": store.review_count,
            "review_reply_rate": store.review_reply_rate,
            "ros_health": store.ros_health,
            "competitor_avg_discount": store.competitor_avg_discount,
            "issues": store.issues or [],
        }
```

- [ ] **Step 2: 提交**
```bash
git add backend/orchestrator/agent_runner.py
git commit -m "feat(orchestrator): add AgentRunner component"
```

- [ ] **Step 3: 创建 `tests/test_agent_runner.py`**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.agents.base import AgentResult, AgentResultStatus
from backend.orchestrator.agent_runner import AgentRunner


class DummyAgent:
    """Minimal agent for testing."""

    def __init__(self, success: bool = True, agent_type: str = "dummy"):
        self.agent_type = agent_type
        self._success = success

    async def run_with_retry(self, context, max_retries=3):
        if self._success:
            return AgentResult(
                agent_type=self.agent_type,
                status=AgentResultStatus.SUCCESS,
                data={"result": "ok"},
            )
        return AgentResult(
            agent_type=self.agent_type,
            status=AgentResultStatus.FAILED,
            error="simulated failure",
        )


class TestAgentRunnerRun:
    async def test_success_updates_context(self):
        agents = {
            "analyzer": DummyAgent(success=True, agent_type="analyzer"),
        }
        runner = AgentRunner(agents)
        context = {"store_id": "test_001"}

        new_context, result = await runner.run("analyzer", context)

        assert result.status == AgentResultStatus.SUCCESS
        assert "analyzer" in new_context
        assert new_context["analyzer"] == {"result": "ok"}
        assert new_context["diagnosis"] == {"result": "ok"}

    async def test_analyzer_sets_diagnosis_in_context(self):
        agents = {
            "analyzer": DummyAgent(success=True, agent_type="analyzer"),
        }
        runner = AgentRunner(agents)
        context = {"store_id": "test_002"}

        _, result = await runner.run("analyzer", context)

        assert "diagnosis" in context
        assert context["diagnosis"] == {"result": "ok"}

    async def test_failure_returns_failed_result(self):
        agents = {
            "web_operator": DummyAgent(success=False, agent_type="web_operator"),
        }
        runner = AgentRunner(agents)
        context = {"store_id": "test_003"}

        _, result = await runner.run("web_operator", context)

        assert result.status == AgentResultStatus.FAILED
        assert result.error == "simulated failure"

    async def test_unknown_agent_type_returns_failed_result(self):
        agents = {}
        runner = AgentRunner(agents)
        context = {"store_id": "test_004"}

        _, result = await runner.run("unknown_agent", context)

        assert result.status == AgentResultStatus.FAILED
        assert result.error == "Unknown agent type: unknown_agent"

    async def test_web_operator_does_not_set_diagnosis(self):
        agents = {
            "web_operator": DummyAgent(success=True, agent_type="web_operator"),
        }
        runner = AgentRunner(agents)
        context = {"store_id": "test_005"}

        _, result = await runner.run("web_operator", context)

        assert "diagnosis" not in context
        assert "web_operator" in context


class TestStoreToDict:
    def test_maps_all_fields(self):
        agents = {}
        runner = AgentRunner(agents)

        mock_store = MagicMock()
        mock_store.store_id = "s001"
        mock_store.name = "测试店"
        mock_store.city = "杭州"
        mock_store.category = "小吃"
        mock_store.rating = 4.5
        mock_store.monthly_orders = 100
        mock_store.gmv_last_7d = 5000.0
        mock_store.review_count = 50
        mock_store.review_reply_rate = 0.8
        mock_store.ros_health = "high"
        mock_store.competitor_avg_discount = 0.85
        mock_store.issues = ["issue1"]

        result = runner.store_to_dict(mock_store)

        assert result["store_id"] == "s001"
        assert result["name"] == "测试店"
        assert result["city"] == "杭州"
        assert result["category"] == "小吃"
        assert result["rating"] == 4.5
        assert result["monthly_orders"] == 100
        assert result["gmv_last_7d"] == 5000.0
        assert result["review_count"] == 50
        assert result["review_reply_rate"] == 0.8
        assert result["ros_health"] == "high"
        assert result["competitor_avg_discount"] == 0.85
        assert result["issues"] == ["issue1"]

    def test_defaults_empty_issues(self):
        agents = {}
        runner = AgentRunner(agents)

        mock_store = MagicMock()
        mock_store.issues = None

        result = runner.store_to_dict(mock_store)

        assert result["issues"] == []
```

- [ ] **Step 4: 运行测试**
```bash
pytest tests/test_agent_runner.py -v
```
Expected: PASS (8 tests)

- [ ] **Step 5: 运行 ruff**
```bash
ruff check backend/orchestrator/agent_runner.py tests/test_agent_runner.py
```
Expected: no errors

- [ ] **Step 6: 提交**
```bash
git add backend/orchestrator/agent_runner.py tests/test_agent_runner.py
git commit -m "test(orchestrator): add AgentRunner tests"
```

---

## Task 4: 重构 WorkflowEngine

**Files:**
- Modify: `backend/orchestrator/engine.py` (重写，~80 行)
- Modify: `backend/orchestrator/__init__.py`

- [ ] **Step 1: 重写 `backend/orchestrator/engine.py`**

保留原文件内容，然后在 `run_workflow` 中重构调用逻辑：

```python
from __future__ import annotations

from datetime import UTC, datetime

from backend.agents.base import AgentResult, AgentResultStatus
from backend.logging_config import get_logger
from backend.models import AgentRun, Report, Store, WorkflowInstance, WorkflowState
from backend.orchestrator.event_emitter import EventEmitter
from backend.orchestrator.state_machine import StateMachine
from backend.orchestrator.agent_runner import AgentRunner

logger = get_logger(__name__)


class WorkflowEngine:
    """
    Orchestrates the multi-agent workflow for a single store.
    Entry point that coordinates StateMachine, EventEmitter, and AgentRunner.
    """

    MAX_RETRIES = 3

    def __init__(
        self,
        db,
        state_machine: StateMachine,
        event_emitter: EventEmitter,
        agent_runner: AgentRunner,
    ) -> None:
        self.db = db
        self.sm = state_machine
        self.emitter = event_emitter
        self.runner = agent_runner

    async def get_or_create_workflow(self, store: Store) -> WorkflowInstance:
        """Delegate to StateMachine."""
        return await self.sm.get_or_create_workflow(self.db, store)

    async def run_workflow(self, store: Store) -> WorkflowInstance:
        """
        Execute the full workflow for a store.
        Runs agents based on current state, handles transitions, and manages failures.
        """
        wf = await self.sm.get_or_create_workflow(self.db, store)
        state = WorkflowState(wf.current_state)

        logger.info(f"Starting workflow for store {store.store_id}, state={state.value}")

        if state == WorkflowState.DONE:
            logger.info("Store already DONE, skipping")
            return wf

        # Determine which agents to run in this state
        agents_to_run = self.sm.get_agents_for_state(state)

        # Build initial context
        context: dict = {
            "store_id": store.store_id,
            "store_data": self.runner.store_to_dict(store),
            "workflow_state": state.value,
        }

        # Run agents and collect results
        any_failure = False

        for agent_type in agents_to_run:
            context, result = await self.runner.run(
                agent_type, context, max_retries=self.MAX_RETRIES
            )
            await self._persist_agent_run(store.id, agent_type, context, result, state)

            if result.status != AgentResultStatus.SUCCESS:
                any_failure = True
                break

        # Determine next state
        if any_failure:
            wf.consecutive_failures += 1
            if wf.consecutive_failures >= self.MAX_RETRIES:
                next_state = WorkflowState.MANUAL_REVIEW
                await self.emitter.create_alert(
                    db=self.db,
                    store_id=store.id,
                    alert_type="consecutive_failure",
                    severity="critical",
                    message=f"连续{self.MAX_RETRIES}次失败，触发人工接管",
                    extra_data={"failures": wf.consecutive_failures},
                )
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

        # Transition state
        if next_state != state:
            await self.sm.transition(self.db, store.id, wf, state, next_state)
            await self.emitter.log_event(
                db=self.db,
                store_id=store.id,
                event_type="state_change",
                from_state=state.value,
                to_state=next_state.value,
                message=f"State transition: {state.value} -> {next_state.value}",
            )

        # Generate report if entering WEEKLY_REPORT
        if next_state == WorkflowState.WEEKLY_REPORT:
            await self._generate_report(store, context, "weekly")

        wf.updated_at = datetime.now(UTC)
        self.db.add(wf)
        await self.db.flush()
        return wf

    async def _persist_agent_run(
        self,
        store_id: int,
        agent_type: str,
        context: dict,
        result: AgentResult,
        state: WorkflowState,
    ) -> None:
        """Persist an agent run record."""
        retry_count = getattr(result, "attempts", 1) - 1

        run = AgentRun(
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
        self.db.add(run)
        await self.db.flush()

        await self.emitter.log_event(
            db=self.db,
            store_id=store_id,
            event_type="agent_run",
            agent_type=agent_type,
            message=f"{agent_type} {result.status.value} ({result.duration_ms}ms)",
            extra_data={"run_id": run.id, "error": result.error},
        )

    async def _generate_report(self, store: Store, context: dict, report_type: str) -> None:
        """Generate and persist a report."""
        report_context: dict = {
            **context,
            "store_id": store.store_id,
            "store_data": self.runner.store_to_dict(store),
            "report_type": report_type,
        }

        _, result = await self.runner.run("reporter", report_context)

        if result.status == AgentResultStatus.SUCCESS:
            report = Report(
                store_id=store.id,
                report_type=report_type,
                content_md=result.data.get("md_report"),
                content_json=result.data.get("json_report"),
            )
            self.db.add(report)
            await self.db.flush()
            await self.emitter.log_event(
                db=self.db,
                store_id=store.id,
                event_type="report_generated",
                message=f"{report_type} report generated",
                extra_data={"report_id": report.id},
            )
            logger.info(f"Report generated for store {store.store_id}")

    async def trigger_manual_takeover(self, store: Store) -> WorkflowInstance:
        """Move a store to MANUAL_REVIEW state."""
        wf = await self.sm.trigger_manual_takeover(self.db, store)
        old_state = WorkflowState(wf.current_state)

        await self.emitter.log_event(
            db=self.db,
            store_id=store.id,
            event_type="manual_takeover",
            from_state=old_state.value,
            to_state=WorkflowState.MANUAL_REVIEW.value,
            message="Manual takeover triggered",
        )
        await self.emitter.create_alert(
            db=self.db,
            store_id=store.id,
            alert_type="manual_takeover",
            severity="warning",
            message="人工接管已触发",
        )
        logger.info(f"Manual takeover triggered for store {store.store_id}")
        return wf
```

- [ ] **Step 2: 更新 `backend/orchestrator/__init__.py`**

```python
from backend.orchestrator.agent_runner import AgentRunner
from backend.orchestrator.engine import WorkflowEngine
from backend.orchestrator.event_emitter import EventEmitter
from backend.orchestrator.state_machine import StateMachine

__all__ = [
    "AgentRunner",
    "EventEmitter",
    "StateMachine",
    "WorkflowEngine",
]
```

- [ ] **Step 3: 运行 ruff 检查**
```bash
ruff check backend/orchestrator/engine.py backend/orchestrator/__init__.py
```
Expected: no errors

- [ ] **Step 4: 提交**
```bash
git add backend/orchestrator/engine.py backend/orchestrator/__init__.py
git commit -m "refactor(orchestrator): split WorkflowEngine into composed components"
```

---

## Task 5: 适配路由层

**Files:**
- Modify: `backend/routes/workflows.py` (适配依赖注入)

**注意：** 此任务需在 `routes/workflows.py` 当前修改完成后执行。如果 `routes/workflows.py` 仍处于不可合并状态，先跳过此任务。

- [ ] **Step 1: 更新 `start_workflow` 中的 Engine 构造方式**

找到 `WorkflowEngine(session)` 调用，替换为：

```python
from backend.agents.analyzer import AnalyzerAgent
from backend.agents.mobile_operator import MobileOperatorAgent
from backend.agents.reporter import ReporterAgent
from backend.agents.web_operator import WebOperatorAgent
from backend.orchestrator import AgentRunner, EventEmitter, StateMachine, WorkflowEngine

agents = {
    "analyzer": AnalyzerAgent(),
    "web_operator": WebOperatorAgent(failure_rate=0.2),
    "mobile_operator": MobileOperatorAgent(failure_rate=0.25),
    "reporter": ReporterAgent(),
}
runner = AgentRunner(agents)
sm = StateMachine()
emitter = EventEmitter()
eng = WorkflowEngine(db=session, state_machine=sm, event_emitter=emitter, agent_runner=runner)
```

同样更新 `manual_takeover` endpoint 中的 `WorkflowEngine(db)` 构造。

- [ ] **Step 2: 运行 ruff**
```bash
ruff check backend/routes/workflows.py
```

- [ ] **Step 3: 提交**
```bash
git add backend/routes/workflows.py
git commit -m "refactor(workflows): wire orchestrator components via DI"
```

---

## Task 6: 迁移并编写 Engine 集成测试

**Files:**
- Create: `tests/test_orchestrator_engine.py`
- Delete: `tests/test_example.py` (确认新测试全部通过后删除)

- [ ] **Step 1: 创建 `tests/test_orchestrator_engine.py`**

```python
"""
Integration tests for the refactored WorkflowEngine.
Mocks StateMachine, EventEmitter, and AgentRunner to test the orchestrator layer.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.agents.base import AgentResult, AgentResultStatus
from backend.models._enums import WorkflowState
from backend.orchestrator.engine import WorkflowEngine


class TestWorkflowEngineIntegration:
    """Test WorkflowEngine orchestration by mocking sub-components."""

    def _make_runner(self, results: dict[str, AgentResult]):
        runner = MagicMock()
        for agent_type, result in results.items():
            runner.run = AsyncMock(return_value=({"store_id": "test"}, result))
        runner.store_to_dict = MagicMock(return_value={"store_id": "test", "name": "店"})
        return runner

    def _make_sm(self, initial_state: WorkflowState = WorkflowState.NEW_STORE):
        wf = MagicMock()
        wf.current_state = initial_state.value
        wf.consecutive_failures = 0
        sm = MagicMock()
        sm.get_or_create_workflow = AsyncMock(return_value=wf)
        sm.get_agents_for_state = MagicMock(return_value=["analyzer"])
        sm.get_next_state = MagicMock(return_value=WorkflowState.DIAGNOSIS)
        sm.transition = AsyncMock()
        return sm, wf

    def _make_emitter(self):
        emitter = MagicMock()
        emitter.log_event = AsyncMock()
        emitter.create_alert = AsyncMock()
        return emitter

    async def test_engine_passes_correct_state_to_sm(self):
        sm, wf = self._make_sm(WorkflowState.DIAGNOSIS)
        runner = self._make_runner({"analyzer": AgentResult(agent_type="analyzer", status=AgentResultStatus.SUCCESS)})
        emitter = self._make_emitter()

        engine = WorkflowEngine(db=MagicMock(), state_machine=sm, event_emitter=emitter, agent_runner=runner)
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        await engine.run_workflow(store)

        sm.get_agents_for_state.assert_called_once_with(WorkflowState.DIAGNOSIS)

    async def test_engine_calls_runner_for_each_agent(self):
        sm, wf = self._make_sm(WorkflowState.DAILY_OPS)
        sm.get_agents_for_state = MagicMock(return_value=["web_operator", "mobile_operator"])

        results = {
            "web_operator": AgentResult(agent_type="web_operator", status=AgentResultStatus.SUCCESS),
            "mobile_operator": AgentResult(agent_type="mobile_operator", status=AgentResultStatus.SUCCESS),
        }
        runner = self._make_runner(results)
        emitter = self._make_emitter()

        engine = WorkflowEngine(db=MagicMock(), state_machine=sm, event_emitter=emitter, agent_runner=runner)
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        await engine.run_workflow(store)

        assert runner.run.call_count == 2

    async def test_engine_stops_on_agent_failure(self):
        sm, wf = self._make_sm(WorkflowState.DIAGNOSIS)
        runner = self._make_runner({"analyzer": AgentResult(agent_type="analyzer", status=AgentResultStatus.FAILED, error="oops")})
        emitter = self._make_emitter()

        engine = WorkflowEngine(db=MagicMock(), state_machine=sm, event_emitter=emitter, agent_runner=runner)
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        await engine.run_workflow(store)

        # Should only call run once (stops after first failure)
        assert runner.run.call_count == 1

    async def test_engine_triggers_manual_review_after_max_failures(self):
        sm, wf = self._make_sm(WorkflowState.DIAGNOSIS)
        wf.consecutive_failures = 2  # Already 2 failures

        runner = self._make_runner({"analyzer": AgentResult(agent_type="analyzer", status=AgentResultStatus.FAILED)})
        emitter = self._make_emitter()

        engine = WorkflowEngine(db=MagicMock(), state_machine=sm, event_emitter=emitter, agent_runner=runner)
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        await engine.run_workflow(store)

        # Should emit critical alert
        emitter.create_alert.assert_called()
        alert_call = emitter.create_alert.call_args
        assert alert_call.kwargs["severity"] == "critical"

    async def test_engine_transitions_on_success(self):
        sm, wf = self._make_sm(WorkflowState.DIAGNOSIS)
        runner = self._make_runner({"analyzer": AgentResult(agent_type="analyzer", status=AgentResultStatus.SUCCESS)})
        emitter = self._make_emitter()

        engine = WorkflowEngine(db=MagicMock(), state_machine=sm, event_emitter=emitter, agent_runner=runner)
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        await engine.run_workflow(store)

        sm.transition.assert_called_once()
        transition_call = sm.transition.call_args
        assert transition_call[0][3] == WorkflowState.DIAGNOSIS
        assert transition_call[0][4] == WorkflowState.FOUNDATION

    async def test_engine_skips_done_state(self):
        sm, wf = self._make_sm(WorkflowState.DONE)
        runner = self._make_runner({})
        emitter = self._make_emitter()

        engine = WorkflowEngine(db=MagicMock(), state_machine=sm, event_emitter=emitter, agent_runner=runner)
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        result_wf = await engine.run_workflow(store)

        # Should not try to run any agents
        runner.run.assert_not_called()
        assert result_wf is wf

    async def test_manual_takeover_calls_sm_and_emitter(self):
        sm, wf = self._make_sm(WorkflowState.DAILY_OPS)
        emitter = self._make_emitter()
        engine = WorkflowEngine(db=MagicMock(), state_machine=sm, event_emitter=emitter, agent_runner=MagicMock())
        store = MagicMock()
        store.id = 1
        store.store_id = "test"

        await engine.trigger_manual_takeover(store)

        sm.trigger_manual_takeover.assert_called_once()
        emitter.log_event.assert_called()
        emitter.create_alert.assert_called()
```

- [ ] **Step 2: 运行测试**
```bash
pytest tests/test_orchestrator_engine.py -v
```
Expected: PASS (7 tests)

- [ ] **Step 3: 运行 ruff**
```bash
ruff check tests/test_orchestrator_engine.py
```

- [ ] **Step 4: 确认旧测试已迁移**
```bash
# 确认 test_state_machine.py 覆盖了 test_example.py 中的 StateMachine 测试
# 确认 test_orchestrator_engine.py 覆盖了 test_example.py 中的 Engine 测试
```

- [ ] **Step 5: 删除旧测试文件**
```bash
git rm tests/test_example.py
git commit -m "test(orchestrator): migrate test_example.py to component tests"
```

---

## Task 7: 全量验证

- [ ] **Step 1: 运行完整测试套件**
```bash
make backend-test
```
Expected: ALL PASS

- [ ] **Step 2: 运行 ruff 检查全部 backend 代码**
```bash
ruff check backend/
```
Expected: no errors

- [ ] **Step 3: 验证行数精简效果**
```bash
wc -l backend/orchestrator/engine.py
# Expected: ~120 行（比原来的 384 行减少约 260 行）
```

- [ ] **Step 4: 提交最终状态**
```bash
git add -A && git commit -m "refactor(orchestrator): complete component split — engine 384->~120 LOC"
```

---

## 自检清单

- [ ] `state_machine.py` 包含所有状态映射逻辑
- [ ] `event_emitter.py` 仅处理 EventLog + Alert 创建
- [ ] `agent_runner.py` 接收 agents dict 并通过 DI 注入
- [ ] `engine.py` 不再直接创建 Agent 实例
- [ ] `__init__.py` 导出所有 4 个类
- [ ] 每个组件有独立测试文件
- [ ] `test_example.py` 已删除，内容迁移完毕
- [ ] `routes/workflows.py` 已适配 DI（若 routes 已就绪）
- [ ] `make backend-test` 全部通过
- [ ] `ruff check backend/` 无错误
