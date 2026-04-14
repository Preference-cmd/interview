import random

from backend.agents.base import AgentResult, AgentStatus, BaseAgent


class AnalyzerAgent(BaseAgent):
    """
    Reads store and competitor data, outputs structured diagnosis (JSON)
    with scores, issue list, and recommended actions.
    """

    def __init__(self):
        super().__init__("analyzer")

    async def execute(self, context: dict) -> AgentResult:
        self._logger.info(f"Analyzing store: {context.get('store_id')}")

        store = context.get("store_data", {})
        issues = store.get("issues", [])

        # Compute health score
        rating = store.get("rating", 0)
        review_rate = store.get("review_reply_rate", 0)
        ros = store.get("ros_health", "low")
        ros_score = {"low": 30, "medium": 60, "high": 90}.get(ros, 50)

        health_score = int(rating * 20 * 0.3 + review_rate * 100 * 0.2 + ros_score * 0.5)
        health_score = min(100, max(0, health_score))

        # Generate issue severity
        issue_analysis = []
        for issue in issues:
            severity = random.choice(["critical", "warning", "info"])
            issue_analysis.append({"issue": issue, "severity": severity})

        # Generate recommendations
        recommendations = []
        if rating < 4.0:
            recommendations.append("提升评分：引导好评，回复差评")
        if review_rate < 0.5:
            recommendations.append("提高评价回复率至50%以上")
        if ros_score < 50:
            recommendations.append("完善ROS基础项，提升曝光权重")
        if store.get("competitor_avg_discount", 0) > 0.8:
            recommendations.append("竞品折扣较高，考虑设置团单优惠")
        if not recommendations:
            recommendations.append("维持当前运营节奏，关注周数据变化")

        result_data = {
            "health_score": health_score,
            "rating": rating,
            "review_reply_rate": review_rate,
            "ros_score": ros_score,
            "issues": issue_analysis,
            "recommendations": recommendations,
            "competitor_avg_discount": store.get("competitor_avg_discount", 0),
            "gmv_last_7d": store.get("gmv_last_7d", 0),
        }

        self._logger.info(
            f"Diagnosis complete: health_score={health_score}, issues={len(issue_analysis)}, "
            f"recommendations={len(recommendations)}"
        )

        return AgentResult(
            agent_type=self.agent_type,
            status=AgentStatus.SUCCESS,
            data=result_data,
        )
