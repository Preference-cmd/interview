from datetime import datetime, UTC
from backend.agents.base import BaseAgent, AgentStatus, AgentResult


class ReporterAgent(BaseAgent):
    """
    Generates daily/weekly markdown or JSON reports with key metric summaries.
    """

    def __init__(self):
        super().__init__("reporter")

    async def execute(self, context: dict) -> AgentResult:
        store = context.get("store_data", {})
        store_id = context.get("store_id", "unknown")
        self._logger.info(f"Generating report for store: {store_id}")

        report_type = context.get("report_type", "daily")

        # Key metrics
        rating = store.get("rating", 0.0)
        gmv = store.get("gmv_last_7d", 0)
        orders = store.get("monthly_orders", 0)
        review_count = store.get("review_count", 0)
        review_reply_rate = store.get("review_reply_rate", 0.0)
        ros_health = store.get("ros_health", "unknown")

        # Health score from diagnosis if available
        diagnosis = context.get("diagnosis", {})
        health_score = diagnosis.get("health_score", "N/A")
        recommendations = diagnosis.get("recommendations", [])

        # Build markdown report
        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
        md_report = self._build_markdown(
            store_id=store_id,
            store_name=store.get("name", "未知门店"),
            report_type=report_type,
            timestamp=now,
            rating=rating,
            gmv=gmv,
            orders=orders,
            review_count=review_count,
            review_reply_rate=review_reply_rate,
            ros_health=ros_health,
            health_score=health_score,
            recommendations=recommendations,
        )

        # JSON report data
        json_data = {
            "store_id": store_id,
            "store_name": store.get("name"),
            "report_type": report_type,
            "generated_at": now,
            "metrics": {
                "rating": rating,
                "gmv_last_7d": gmv,
                "monthly_orders": orders,
                "review_count": review_count,
                "review_reply_rate": round(review_reply_rate * 100, 1),
                "ros_health": ros_health,
                "health_score": health_score,
            },
            "recommendations": recommendations,
            "agent_runs": context.get("agent_runs", []),
        }

        self._logger.info(
            f"Report generated for {store.get('name', store_id)}: {report_type} report, "
            f"gmv={gmv}, rating={rating}"
        )

        return AgentResult(
            agent_type=self.agent_type,
            status=AgentStatus.SUCCESS,
            data={"md_report": md_report, "json_report": json_data},
        )

    def _build_markdown(
        self,
        store_id,
        store_name,
        report_type,
        timestamp,
        rating,
        gmv,
        orders,
        review_count,
        review_reply_rate,
        ros_health,
        health_score,
        recommendations,
    ) -> str:
        report_type_cn = "日报" if report_type == "daily" else "周报"
        ros_health_cn = {"low": "低", "medium": "中", "high": "高"}.get(
            ros_health, "未知"
        )

        lines = [
            f"# {store_name} {report_type_cn}",
            f"**门店ID**: {store_id}  |  **日期**: {timestamp}",
            "",
            "## 核心指标",
            "",
            "| 指标 | 数值 |",
            "|------|------|",
            f"| 评分 | {rating} ⭐ |",
            f"| 近7天GMV | ¥{gmv:,.2f} |",
            f"| 月订单量 | {orders} |",
            f"| 评价数 | {review_count} |",
            f"| 评价回复率 | {review_reply_rate * 100:.1f}% |",
            f"| ROS健康度 | {ros_health_cn} |",
            f"| 综合健康分 | {health_score} |",
            "",
            "## 运营建议",
            "",
        ]

        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"{i}. {rec}")
        else:
            lines.append("当前状态良好，维持日常运营。")

        lines.extend(
            [
                "",
                "---",
                f"*由 Multi-Agent Ops 系统自动生成 | {timestamp}*",
            ]
        )

        return "\n".join(lines)

