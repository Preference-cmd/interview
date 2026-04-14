# 开发状态追踪

> 最后更新：2026-04-14

---

## 一、架构评估总结（Backend）

### 当前状态：功能完整，质量待提升

| 维度 | 评分 | 说明 |
|------|------|------|
| 功能完备性 | 9/10 | 状态机/4类Agent/全部API/测试 均已实现 |
| 数据完整性 | 7/10 | FK正确，缺唯一约束和关键索引 |
| 并发安全 | 4/10 | 无锁，竞态条件存在 |
| 事务边界 | 6/10 | 每 route 级别 commit，无细粒度控制 |
| 可扩展性 | 5/10 | 单进程内存队列，无 job 持久化 |

---

## 二、已知问题（按优先级）

### 🔴 P0 — 必须修复

- **[DB] `workflow_instances.store_id` 缺唯一约束**
  - 现状：`uselist=False` 声明 1:1，但无 DB 层唯一索引
  - 风险：并发创建可能产生两条 workflow 记录
  - 修复：`UniqueConstraint('store_id')` 或 `unique=True` 索引

- **[DB] 缺关键查询索引**
  - `agent_runs(store_id, created_at)` — 按 store 查运行历史
  - `event_logs(store_id, created_at)` — 按 store 查事件时间线
  - `alerts(store_id, acknowledged)` — 告警查询
  - `reports(store_id, report_type)` — 报告查询

### 🟡 P1 — 应该修复

- **[Sync/Async] 数据库层不一致**
  - `database.py` 定义了 `AsyncSessionLocal` 但从未使用
  - `get_db()` 是 async generator，但实际产出 sync Session
  - 建议：统一到纯 sync（删 `AsyncSessionLocal`），或升级到纯 async

- **[Agent] `AgentStatus` 重复定义**
  - `models.py` 和 `agents/base.py` 各定义一份
  - 建议：统一从 `agents.base` import

- **[Agent] `AgentRun.retry_count` 永远是 0**
  - `engine.py:303` 写入 0，未从 agent 获取真实值
  - 字段有语义但实际是死的

- **[Engine] 并发竞态**
  - 两个并发 `/stores/{id}/start` 请求可能同时创建 workflow
  - 无数据库行锁或 `SELECT FOR UPDATE`

### 🟢 P2 — 可选改进

- **[Engine] 单次运行只处理一个状态**
  - 完整流程 NEW_STORE→DONE 需要 6 次独立 `run_workflow()` 调用
  - 如需连续执行，需外部调度器多次触发

- **[Agent] `run_with_retry` 中 `failure_rate` 重复赋值**
  - `agent.failure_rate` 和局部变量 `failure_rate` 并存
  - 代码冗余

- **[Model] `datetime.utcnow()` 已迁移至 `datetime.now(UTC)`**
  - 已修复，见下方"已完成"列表

---

## 三、已完成的修复

| 日期 | 修复内容 |
|------|---------|
| 2026-04-14 | `datetime.utcnow()` → `datetime.now(UTC)`（models.py, engine.py, reporter.py） |
| 2026-04-14 | `tool.uv.dev-dependencies` → `dependency-groups.dev`（pyproject.toml） |
| 2026-04-14 | 测试 `run_until_complete` 反模式 → `@pytest.mark.asyncio` + `await` |
| 2026-04-14 | 新建 `README.md`（项目说明） |
| 2026-04-14 | 新建 `ARCHITECTURE.md`（架构文档） |

---

## 四、待创建文档

| 文件 | 状态 | 说明 |
|------|------|------|
| `AI_USAGE.md` | ⬜ 未创建 | AI 工具使用记录（doc/ 目标要求） |

---

## 五、技术债务

```
# TODO: replace with real Redis  (engine.py — 内存队列替代方案标注)
# TODO: upgrade to full async DB session (database.py — AsyncSessionLocal 未使用)
```

---

## 六、测试状态

```
16 passed, 0 warnings
- 6 state transition tests
- 5 workflow engine tests
- 2 retry logic tests (async, proper await)
- 2 manual takeover tests
- 1 reporter idempotency test
```

---

## 七、决策记录

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-04-14 | 使用 sync SQLAlchemy 而非 async | SQLite + 单线程场景下 sync 足够，避免 async 复杂度 |
| 2026-04-14 | 使用 `asyncio.create_task()` 触发后台 workflow | 轻量，无需引入 Celery/Redis |
| 2026-04-14 | 所有 agent 均为 mock | 无真实美团/开店宝/企微 接入需求 |
