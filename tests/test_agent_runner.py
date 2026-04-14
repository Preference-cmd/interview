import pytest
from unittest.mock import MagicMock

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


@pytest.mark.asyncio
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
