import asyncio
import random
from backend.agents.base import BaseAgent, AgentStatus, AgentResult


class MobileOperatorAgent(BaseAgent):
    """
    Simulates App actions (material check, activity confirm).
    Simulates 2-5s delay, random failure.
    """

    def __init__(self, failure_rate: float = 0.25):
        super().__init__("mobile_operator")
        self.failure_rate = failure_rate

    async def execute(self, context: dict) -> AgentResult:
        self._logger.info(
            f"MobileOperator executing for store: {context.get('store_id')}"
        )

        # Simulate delay 2-5 seconds
        delay = random.uniform(2.0, 5.0)
        self._logger.info(f"Simulating mobile operation ({delay:.1f}s)...")
        await asyncio.sleep(delay)

        store = context.get("store_data", {})
        actions_taken = []

        # Simulate material check
        material_status = random.choice(["approved", "needs_review", "rejected"])
        actions_taken.append(
            {"action": "check_material", "status": material_status}
        )

        # Simulate activity confirmation
        if store.get("ros_health") in ["low", "medium"]:
            actions_taken.append({"action": "confirm_activity", "status": "confirmed"})
            self._logger.info("Activity confirmed via mobile app")

        # ROS snapshot
        ros_snapshot = {
            "ros_health": store.get("ros_health", "unknown"),
            "rating": store.get("rating", 0),
            "review_count": store.get("review_count", 0),
            "review_reply_rate": store.get("review_reply_rate", 0),
        }
        actions_taken.append({"action": "capture_ros_snapshot", "data": ros_snapshot})

        # Check if material needs attention
        if material_status == "rejected":
            self._logger.warning("Material rejected, needs manual review")

        return AgentResult(
            agent_type=self.agent_type,
            status=AgentStatus.SUCCESS,
            data={
                "actions_taken": actions_taken,
                "delay_seconds": round(delay, 2),
                "material_status": material_status,
            },
        )
