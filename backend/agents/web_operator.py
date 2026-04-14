import asyncio
import random

from backend.agents.base import AgentResult, AgentStatus, BaseAgent


class WebOperatorAgent(BaseAgent):
    """
    Simulates backend actions (create deals, set promotions).
    Simulates 1-3s delay, random failure.
    """

    def __init__(self, failure_rate: float = 0.2):
        super().__init__("web_operator")
        self.failure_rate = failure_rate

    async def execute(self, context: dict) -> AgentResult:
        self._logger.info(f"WebOperator executing for store: {context.get('store_id')}")

        # Simulate delay 1-3 seconds
        delay = random.uniform(1.0, 3.0)
        self._logger.info(f"Simulating backend operation ({delay:.1f}s)...")
        await asyncio.sleep(delay)

        store = context.get("store_data", {})
        diagnosis = context.get("diagnosis", {})

        # Simulate actions based on diagnosis
        actions_taken = []
        issues = store.get("issues", [])

        if "无推广活动" in issues:
            actions_taken.append({"action": "create_deal", "status": "success"})
            self._logger.info("Created new deal group")

        if "图片质量低" in issues:
            actions_taken.append({"action": "upload_images", "status": "success"})
            self._logger.info("Uploaded store images")

        if diagnosis.get("recommendations"):
            for rec in diagnosis.get("recommendations", [])[:2]:
                if "团单" in rec or "优惠" in rec:
                    actions_taken.append({"action": "set_discount", "status": "success"})
                    self._logger.info(f"Set discount: {rec}")

        # Default: check ROS status
        actions_taken.append({"action": "check_ros", "status": "success"})
        actions_taken.append({"action": "sync_platform_data", "status": "success"})

        return AgentResult(
            agent_type=self.agent_type,
            status=AgentStatus.SUCCESS,
            data={
                "actions_taken": actions_taken,
                "delay_seconds": round(delay, 2),
            },
        )
