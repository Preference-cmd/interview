# AI 编程机试（2.5～3 小时）

## 工具使用规则

允许并鼓励使用以下工具：Claude Code、Cursor、ChatGPT / 其他 AI 助手、官方文档、搜索引擎。

但你必须提交 `AI_USAGE.md`，详细说明你如何使用 AI 完成任务（详见"提交物要求"部分）。

---

## A. 后端 Orchestrator

实现一个简化版工作流引擎，支持以下状态流转：

```
NEW_STORE → DIAGNOSIS → FOUNDATION → DAILY_OPS → WEEKLY_REPORT → DONE
任意阶段异常 → MANUAL_REVIEW
```

必须满足：

- 支持四类 Agent 的执行与编排
- 支持状态流转与事件记录
- 支持失败重试（最多 3 次）
- 连续失败后进入人工接管队列
- 所有关键动作有结构化日志
- 支持最基本的查询 API

---

## B. 四类 Agent 的 Mock 实现

不要求真实接入美团/开店宝/企微，但要有 mock 行为：

| Agent | Mock 行为说明 |
|-------|-------------|
| **AnalyzerAgent** | 读取门店与竞品数据，输出结构化诊断结果（JSON，含评分、问题列表、建议操作） |
| **WebOperatorAgent** | 模拟后台动作（如创建团单 / 设置推广），模拟 1～3 秒延迟，可随机失败 |
| **MobileOperatorAgent** | 模拟 App 动作（如素材检查 / 活动确认），模拟 2～5 秒延迟，可随机失败 |
| **ReporterAgent** | 生成日报/周报 markdown 或 JSON，包含关键指标摘要 |

---

## C. 最少 API

至少实现以下接口：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/stores/import` | POST | 批量导入门店数据 |
| `/stores/{id}/start` | POST | 启动指定门店的工作流 |
| `/stores/{id}/status` | GET | 查询门店当前状态和最近 Agent 执行情况 |
| `/stores/{id}/timeline` | GET | 查询门店事件时间线 |
| `/dashboard/summary` | GET | 全局概览：状态分布、异常数、队列积压 |
| `/stores/{id}/manual-takeover` | POST | 触发人工接管 |

---

## D. 前端最小监控台

实现一个简单 dashboard，至少包含：

- 门店列表（含当前状态）
- Agent 运行状态 / 最近心跳
- 异常告警展示
- 单店事件时间线
- 至少 1 个图表（如状态分布、失败率、队列积压等）

React / Vue / Next.js 均可。

---

## E. 最少测试

至少补 1 个测试，建议任选其一：

- 状态流转测试
- 重试逻辑测试
- 周报幂等测试
- 人工接管测试

---

## 中途变更需求

> 注意：机试进行中会收到一次临时产品变更需求，请做好心理准备。这是考核的一部分，重点看你能否快速用 AI 工具做重构，而不是从零重来。

---

## 五、提交物要求

| 文件 | 内容要求 | 重要程度 |
|------|---------|---------|
| `README.md` | 项目说明、启动方式、技术栈说明 | 必须 |
| `ARCHITECTURE.md` | 架构图、模块说明、状态机设计、数据流 | 必须 |
| `AI_USAGE.md` | AI 使用记录（详见下方） | **核心评估文件** |
| 源码仓库 | 可运行的完整代码 | 必须 |

---

## AI_USAGE.md 写作要求（非常重要）

> 这个文件是核心评估文件。它直接测试你"会不会驾驭 AI"，而不只是"有没有用 AI"。请认真对待。

`AI_USAGE.md` 必须写清楚以下 5 点：

| # | 内容 | 说明 |
|---|------|------|
| 1 | 使用了哪些 AI 工具 | 列出所有使用的工具名称和版本 |
| 2 | 5 条最关键的 prompt / 指令 | 展示你如何向 AI 下达具体指令，而不是泛泛地说"帮我写个 xxx" |
| 3 | 哪 2 次 AI 给了错误建议，你是怎么修正的 | 说明 AI 哪里错了、为什么错、你怎么发现的、怎么修的 |
| 4 | 哪些文件主要由 AI 生成，哪些部分是你自己重写的 | 区分清楚 AI 和人工的贡献边界 |
| 5 | 你如何验证 AI 生成代码可用 | 单元测试、手动测试、日志检查等具体方法 |

### 好的 AI_USAGE.md 长什么样

#### 示例 Prompt 记录（好的写法）：

**Prompt #1: 生成数据模型**

```
目标：生成 SQLAlchemy 数据模型
约束：必须包含 store、workflow_instance、agent_run、event_log、alert、report 六张表
要求：每张表注明字段类型、索引、外键关系；agent_run 需要有 retry_count 和 error_msg 字段
输出格式：Python 文件，可直接导入使用
```

**结果**：AI 生成的模型基本可用，但缺少 `idempotency_key` 字段，我手动补充。

#### 示例错误修正记录（好的写法）：

**AI 错误 #1: 状态流转缺少校验**

- **问题**：AI 生成的状态机允许从任意状态跳转到任意状态，没有白名单校验
- **发现方式**：手动测试时发现可以从 NEW_STORE 直接跳到 DONE
- **修复**：添加 `VALID_TRANSITIONS` 字典，在 `transition()` 方法中校验 from→to 合法性
- **教训**：AI 容易忽略业务约束，状态机相关代码必须自己审查

---

## 六、Starter Repo 说明

我们提供了一个 starter repo，已帮你完成基础配置。请基于此开发。

### 目录结构

```
multi-agent-ops/
├── backend/
│   ├── main.py              # FastAPI 入口，已配置 CORS
│   ├── models.py            # SQLAlchemy 模型骨架（store 表已定义）
│   ├── schemas.py           # Pydantic schema 骨架
│   ├── database.py          # SQLite 连接配置
│   ├── agents/
│   │   ├── base.py          # BaseAgent 抽象类（已定义 execute 接口）
│   │   └── __init__.py
│   ├── orchestrator/
│   │   └── engine.py        # WorkflowEngine 骨架（已定义状态枚举）
│   └── requirements.txt     # fastapi, uvicorn, sqlalchemy, redis
├── frontend/
│   ├── package.json         # React + Vite 已配置
│   ├── src/
│   │   ├── App.jsx          # 基础路由已配置
│   │   ├── api.js           # API 调用封装
│   │   └── components/      # 空目录
│   └── vite.config.js
├── mock_data/
│   ├── stores.json          # 10 家模拟门店数据
│   ├── competitors.json     # 竞品数据
│   └── reviews.json         # 模拟评价数据
├── tests/
│   └── test_example.py      # 示例测试（可运行）
├── Makefile                 # make run / make test 快捷命令
└── README.md                # 启动说明
```

### 已提供的 BaseAgent 抽象类

你需要继承此类实现四个具体 Agent：

```python
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional

class AgentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class AgentResult:
    agent_type: str
    status: AgentStatus
    data: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: int = 0

class BaseAgent(ABC):
    def __init__(self, agent_type: str):
        self.agent_type = agent_type

    @abstractmethod
    async def execute(self, context: dict) -> AgentResult:
        """Execute agent task. Implement in subclass."""
        pass

    async def run_with_retry(self, context, max_retries=3):
        for attempt in range(max_retries):
            result = await self.execute(context)
            if result.status == AgentStatus.SUCCESS:
                return result
            # TODO: implement retry logic with backoff
        return result
```

### Mock 数据样本（stores.json 节选）

```json
[
  {
    "store_id": "mt_001",
    "name": "张姐麻辣烫（西湖店）",
    "city": "杭州",
    "category": "小吃快餐",
    "rating": 4.2,
    "monthly_orders": 320,
    "gmv_last_7d": 8500,
    "review_count": 156,
    "review_reply_rate": 0.45,
    "ros_health": "medium",
    "competitor_avg_discount": 0.75,
    "issues": ["图片质量低", "无推广活动", "评价回复率低"]
  },
  {
    "store_id": "mt_002",
    "name": "老王黄焖鸡（滨江店）",
    "city": "杭州",
    "category": "美食",
    "rating": 3.6,
    "monthly_orders": 0,
    "gmv_last_7d": 0,
    "review_count": 12,
    "review_reply_rate": 0.08,
    "ros_health": "low",
    "competitor_avg_discount": 0.82,
    "issues": ["新店冷启动", "评分低", "无团单"]
  }
]
```

---

## 常见问题 FAQ

| 问题 | 回答 |
|------|------|
| Q: 可以换技术栈吗？ | A: 可以，但不额外加分。推荐使用默认技术栈以节省时间。 |
| Q: 前端需要很漂亮吗？ | A: 不需要。重点是信息架构合理、能展示状态和异常，而不是视觉设计。 |
| Q: 需要真实接入美团/企微吗？ | A: 不需要。所有外部服务用 mock 实现即可。 |
| Q: AI 可以帮我写全部代码吗？ | A: 可以让 AI 生成代码，但你必须理解每一行代码的含义。答辩会追问细节。 |
| Q: 中途变更需求大概什么时候来？ | A: 大约在机试开始 60 分钟后，具体时间可能有浮动。 |
| Q: 笔试可以用 AI 吗？ | A: 不可以。笔试阶段考察的是思维能力，请独立作答。 |
| Q: 机试做不完怎么办？ | A: 做不完没关系，我们看的是已完成部分的质量和你的工作方式，而不是完成度。核心功能做好比所有功能做一半更好。 |
| Q: Redis 必须用真实的吗？ | A: 不需要。可以用内存 dict 模拟 Redis 行为，但需要在代码中标注 `# TODO: replace with real Redis`。 |

---

祝你考试顺利，展现真正的实力！
