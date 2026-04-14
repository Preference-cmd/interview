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
