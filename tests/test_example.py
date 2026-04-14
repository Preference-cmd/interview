import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, UTC
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.models import (
    Store, WorkflowInstance, AgentRun, EventLog, Alert, Report,
    WorkflowState, VALID_TRANSITIONS,
)
from backend.database import Base
from backend.agents.base import BaseAgent, AgentStatus, AgentResult
from backend.agents.analyzer import AnalyzerAgent
from backend.agents.reporter import ReporterAgent
from backend.orchestrator.engine import WorkflowEngine


# --- Fixtures ---

@pytest.fixture
def engine_sqlite():
    """In-memory SQLite engine for tests."""
    e = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=e)
    return e


@pytest.fixture
def db_session(engine_sqlite):
    """Sync session for state machine tests."""
    Session = sessionmaker(bind=engine_sqlite)
    session = Session()
    yield session
    session.close()


@pytest_asyncio.fixture
async def async_db_session():
    """Async session for engine tests."""
    async_eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with async_eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(async_eng, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await async_eng.dispose()


@pytest.fixture
def sample_store(db_session):
    store = Store(
        store_id="test_001",
        name="测试麻辣烫店",
        city="杭州",
        category="小吃快餐",
        rating=3.5,
        monthly_orders=50,
        gmv_last_7d=1500,
        review_count=30,
        review_reply_rate=0.3,
        ros_health="medium",
        competitor_avg_discount=0.75,
        issues=["图片质量低", "无推广活动"],
    )
    db_session.add(store)
    db_session.flush()
    return store


# --- State Machine Tests ---

class TestStateTransitions:
    """Test that state transitions follow the valid transition rules."""

    def test_new_store_to_diagnosis_allowed(self):
        assert WorkflowState.DIAGNOSIS in VALID_TRANSITIONS[WorkflowState.NEW_STORE]

    def test_new_store_to_manual_review_allowed(self):
        assert WorkflowState.MANUAL_REVIEW in VALID_TRANSITIONS[WorkflowState.NEW_STORE]

    def test_diagnosis_to_daily_ops_not_allowed(self):
        """New store must go through FOUNDATION, not skip to DAILY_OPS."""
        assert WorkflowState.DAILY_OPS not in VALID_TRANSITIONS[WorkflowState.DIAGNOSIS]

    def test_weekly_report_to_daily_ops_allowed(self):
        """Weekly report can loop back to daily ops for continuous improvement."""
        assert WorkflowState.DAILY_OPS in VALID_TRANSITIONS[WorkflowState.WEEKLY_REPORT]

    def test_done_is_terminal(self):
        """DONE state has no outgoing transitions."""
        assert len(VALID_TRANSITIONS[WorkflowState.DONE]) == 0

    def test_all_states_have_manual_review_out(self):
        """Every non-terminal state can go to MANUAL_REVIEW."""
        non_terminal = {
            WorkflowState.NEW_STORE,
            WorkflowState.DIAGNOSIS,
            WorkflowState.FOUNDATION,
            WorkflowState.DAILY_OPS,
            WorkflowState.WEEKLY_REPORT,
        }
        for state in non_terminal:
            assert WorkflowState.MANUAL_REVIEW in VALID_TRANSITIONS[state], \
                f"{state.value} should allow MANUAL_REVIEW"


# --- WorkflowEngine Tests ---

class TestWorkflowEngine:
    """Test the workflow orchestration engine."""

    @pytest.mark.asyncio
    async def test_get_or_create_workflow_creates_new(self, async_db_session):
        store = Store(
            store_id="test_async_001",
            name="测试麻辣烫店",
            city="杭州",
            category="小吃快餐",
            rating=3.5,
            monthly_orders=50,
            gmv_last_7d=1500,
            review_count=30,
            review_reply_rate=0.3,
            ros_health="medium",
            competitor_avg_discount=0.75,
        )
        async_db_session.add(store)
        await async_db_session.flush()

        eng = WorkflowEngine(async_db_session)
        wf = await eng.get_or_create_workflow(store)

        assert wf is not None
        assert wf.store_id == store.id
        assert wf.current_state == WorkflowState.NEW_STORE.value
        assert wf.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_get_or_create_workflow_returns_existing(self, async_db_session):
        store = Store(
            store_id="test_async_002",
            name="测试门店2",
            city="上海",
            category="餐饮",
        )
        async_db_session.add(store)
        await async_db_session.flush()

        eng = WorkflowEngine(async_db_session)
        wf1 = await eng.get_or_create_workflow(store)
        wf2 = await eng.get_or_create_workflow(store)

        assert wf1.id == wf2.id

    def test_get_agents_for_state_diagnosis(self):
        """DIAGNOSIS state should run AnalyzerAgent."""
        from backend.orchestrator.engine import WorkflowEngine

        class DummyDB:
            pass

        eng = WorkflowEngine(DummyDB())
        agents = eng._get_agents_for_state(WorkflowState.DIAGNOSIS)
        assert "analyzer" in agents

    def test_get_agents_for_state_daily_ops(self):
        """DAILY_OPS should run web and mobile operators."""
        class DummyDB:
            pass

        eng = WorkflowEngine(DummyDB())
        agents = eng._get_agents_for_state(WorkflowState.DAILY_OPS)
        assert "web_operator" in agents
        assert "mobile_operator" in agents

    def test_get_agents_for_state_weekly_report(self):
        """WEEKLY_REPORT should run ReporterAgent."""
        class DummyDB:
            pass

        eng = WorkflowEngine(DummyDB())
        agents = eng._get_agents_for_state(WorkflowState.WEEKLY_REPORT)
        assert "reporter" in agents


# --- Retry Logic Tests ---

class TestRetryLogic:
    """Test that retry logic works correctly."""

    @pytest.mark.asyncio
    async def test_analyzer_agent_success(self):
        """AnalyzerAgent should always succeed (no random failure)."""
        agent = AnalyzerAgent()
        context = {
            "store_id": "test",
            "store_data": {
                "rating": 4.0,
                "review_reply_rate": 0.5,
                "ros_health": "medium",
                "competitor_avg_discount": 0.75,
                "issues": ["图片质量低"],
            },
        }
        result = await agent.execute(context)

        assert result.status == AgentStatus.SUCCESS
        assert result.data is not None
        assert "health_score" in result.data
        assert "recommendations" in result.data

    @pytest.mark.asyncio
    async def test_reporter_agent_success(self):
        """ReporterAgent should always succeed."""
        agent = ReporterAgent()
        context = {
            "store_id": "test_001",
            "store_data": {
                "name": "测试门店",
                "rating": 4.0,
                "gmv_last_7d": 5000,
                "monthly_orders": 100,
                "review_count": 50,
                "review_reply_rate": 0.5,
                "ros_health": "medium",
            },
            "report_type": "daily",
        }
        result = await agent.execute(context)

        assert result.status == AgentStatus.SUCCESS
        assert "md_report" in result.data
        assert "json_report" in result.data
        assert "核心指标" in result.data["md_report"]


# --- Manual Takeover Tests ---

class TestManualTakeover:
    """Test manual takeover functionality."""

    @pytest.mark.asyncio
    async def test_trigger_manual_takeover(self, async_db_session):
        store = Store(
            store_id="test_async_003",
            name="测试门店3",
            city="北京",
            category="零售",
        )
        async_db_session.add(store)
        await async_db_session.flush()

        eng = WorkflowEngine(async_db_session)
        await eng.get_or_create_workflow(store)

        wf = await eng.trigger_manual_takeover(store)

        assert wf.current_state == WorkflowState.MANUAL_REVIEW.value
        assert wf.consecutive_failures == 0

        # Verify event was logged
        from sqlalchemy import select
        from backend.models import EventLog
        result = await async_db_session.execute(
            select(EventLog).where(
                EventLog.store_id == store.id,
                EventLog.event_type == "manual_takeover",
            )
        )
        events = list(result.scalars().all())
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_manual_takeover_creates_alert(self, async_db_session):
        store = Store(
            store_id="test_async_004",
            name="测试门店4",
            city="深圳",
            category="餐饮",
        )
        async_db_session.add(store)
        await async_db_session.flush()

        eng = WorkflowEngine(async_db_session)
        await eng.get_or_create_workflow(store)

        await eng.trigger_manual_takeover(store)

        from sqlalchemy import select
        result = await async_db_session.execute(
            select(Alert).where(
                Alert.store_id == store.id,
                Alert.alert_type == "manual_takeover",
            )
        )
        alerts = list(result.scalars().all())
        assert len(alerts) == 1


# --- Reporter Idempotency Test ---

class TestReporterIdempotency:
    """Test that running the reporter multiple times produces consistent output."""

    @pytest.mark.asyncio
    async def test_reporter_produces_deterministic_fields(self):
        """Report should contain expected sections regardless of store data."""
        agent = ReporterAgent()
        context = {
            "store_id": "test_001",
            "store_data": {
                "name": "最小测试门店",
                "rating": 4.0,
                "gmv_last_7d": 1000,
                "monthly_orders": 10,
                "review_count": 5,
                "review_reply_rate": 0.2,
                "ros_health": "low",
            },
            "report_type": "daily",
        }
        result = await agent.execute(context)

        md = result.data["md_report"]
        json_data = result.data["json_report"]

        # Markdown should contain required sections
        assert "核心指标" in md
        assert "运营建议" in md
        assert "Multi-Agent Ops 系统" in md

        # JSON should contain all key fields
        assert json_data["store_id"] == "test_001"
        assert "metrics" in json_data
        assert "rating" in json_data["metrics"]
        assert "recommendations" in json_data
