# Store Detail Modal — Design Specification

## Status: Draft

> 原 `STORE-DETAIL-DESIGN.md` 已废弃，改为模态浮层方案。

## 1. Overview

在 Store List 表格中，点击任意一行 → 弹出模态浮层展示门店详情。浮层左右分栏：左侧展示工作流进度（垂直步骤条 + 当前步骤详情 + 关键指标），右侧展示近期动态时间线。支持 `MANUAL_REVIEW` 失败状态的特殊 UI。

## 2. Interaction

- **触发**：点击 Store List 表格任意行
- **关闭**：点击浮层遮罩 / header 关闭按钮 / ESC 键
- **数据获取**：浮层打开后并发请求 `/stores/{id}`、`/stores/{id}/status`、`/stores/{id}/timeline`

## 3. Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  Modal Overlay (backdrop blur)                                        │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ HEADER                                                          │  │
│  │ [门店头像] [名称 / 城市 / 评分]        [状态徽章] [操作按钮] [✕]  │  │
│  ├──────────────────────────┬─────────────────────────────────────┤  │
│  │ LEFT (flex: 1)          │ RIGHT (flex: 1)                     │  │
│  │                          │                                     │  │
│  │ 工作流进度 (section label) │ 近期动态 (section label)            │  │
│  │ ┌──────────────────────┐ │                                     │  │
│  │ │ 垂直步骤条            │ │  [activity]                         │  │
│  │ │ ○ 1. New Store  ✓   │ │  [activity]                         │  │
│  │ │ ● 2. Diagnosis  ←   │ │  [activity]                         │  │
│  │ │ ○ 3. Foundation     │ │  ...                                │  │
│  │ │ ○ 4. Daily Ops      │ │                                     │  │
│  │ │ ○ 5. Weekly Report  │ │                                     │  │
│  │ │ ○ 6. Done           │ │                                     │  │
│  │ └──────────────────────┘ │                                     │  │
│  │                          │                                     │  │
│  │ 当前步骤详情卡片           │                                     │  │
│  │ ├ 步骤标题 + 状态标签      │                                     │  │
│  │ ├ 步骤描述                │                                     │  │
│  │ ├ Agent 标签组            │                                     │  │
│  │ ├ 指标网格 (2×2)          │                                     │  │
│  │ └ 待处理问题标签列表       │                                     │  │
│  │                          │                                     │  │
│  │ [失败日志卡片] ← 仅 MANUAL_REVIEW 时显示                          │  │
│  ├──────────────────────────┴─────────────────────────────────────┤  │
│  │ FOOTER: [关闭按钮]                        [继续下一步]           │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.1 Header

| 元素 | 说明 |
|------|------|
| 门店头像 | 44×44，圆角 12px，terracotta 背景 + 名称首字 |
| 门店名称 | 18px Anthropic Serif bold |
| 门店元信息 | 12px，颜色 #999，格式：`城市 · 类目 · store_id · 评分 ⭐` |
| 状态徽章 | 状态对应色：DIAGNOSIS=蓝、FOUNDATION=紫、DAILY_OPS=橙、WEEKLY_REPORT=绿、DONE=深绿、MANUAL_REVIEW=红 |
| 操作按钮 | 人工接管（secondary）、启动/重试（primary terracotta 或红色） |
| 关闭按钮 | ✕ 图标，位于最右侧 |

### 3.2 Left Column — 工作流进度

**垂直步骤条**（6 个步骤，NEW_STORE → DIAGNOSIS → FOUNDATION → DAILY_OPS → WEEKLY_REPORT → DONE）：

| 状态 | 圆点样式 |
|------|---------|
| 已完成 | 绿色填充 + ✓ 图标 |
| 当前 | terracotta 填充 + 序号 + 外发光 |
| 未开始 | 灰色空心圆 |
| MANUAL_REVIEW | 红色空心 + ! 图标（单独一行，不在线性步骤内）|

步骤名下方显示中文副标题（如"健康诊断"）。

**当前步骤详情卡片**（始终显示，根据当前 state 切换内容）：

- 卡片标题 + 状态标签（"进行中" / "已完成" / "等待处理"）
- 步骤描述文字（来自 StateMachine 配置或硬编码）
- Agent 标签组（如 `Analyzer Agent`、`Web Operator Agent` 等）
- 2×2 指标网格：`评分`、`月订单量`、`7日GMV`、`评价回复率`。数字超出阈值时用警告色/红色标注
- 待处理问题列表（来自 `store.issues`），红色标签

**失败日志卡片**（仅 `MANUAL_REVIEW` 状态时显示，在详情卡片下方）：

- 橙色背景 `#fff7ed`，橙色边框
- 标题：「最近失败详情」
- 列出最近 3 次失败：时间戳 + 错误信息

### 3.3 Right Column — 近期动态

垂直时间线，最新在上：

- 左侧连接线（Border Cream 色）
- 每个节点：圆点（颜色对应事件类型）+ 内容块
- 内容块：事件描述 + Agent 标签 + 时间戳 + 耗时（ms）
- 事件类型 → 颜色映射：
  - `state_change` → 蓝色
  - `agent_run` + success → 绿色
  - `agent_run` + failed → 橙色
  - `report_generated` → 绿色
  - `manual_takeover` → 红色

### 3.4 Footer

- 左侧：关闭按钮（secondary）
- 右侧：继续下一步按钮（primary，调用 `/stores/{id}/start`）

## 4. State Variants

| State | Header 徽章色 | 步骤条高亮 | 详情卡片内容 | 失败日志 |
|-------|-------------|-----------|------------|---------|
| `NEW_STORE` | 灰色 | 全灰 | 提示"尚未启动工作流" | 无 |
| `DIAGNOSIS` | 蓝色 | 当前高亮 | Analyzer Agent + 诊断指标 | 无 |
| `FOUNDATION` | 紫色 | 当前高亮 | Web/Mobile Operator + 基建指标 | 无 |
| `DAILY_OPS` | 橙色 | 当前高亮 | 所有 Agent + 运营指标 | 无 |
| `WEEKLY_REPORT` | 绿色 | 当前高亮 | Reporter Agent + 报告指标 | 无 |
| `DONE` | 深绿 | 全部 ✓ | "工作流已完成" | 无 |
| `MANUAL_REVIEW` | 红色 | 红色! + 失败步骤×3 | 失败详情 + 橙色失败日志卡片 | 显示 |

## 5. API Calls

浮层打开时并发请求：

| 接口 | 用途 |
|------|------|
| `GET /stores/{id}` | 门店基本信息、issues |
| `GET /stores/{id}/status` | 当前 state、consecutive_failures、recent_agent_runs |
| `GET /stores/{id}/timeline` | 事件时间线（用于右侧动态） |

## 6. Loading & Error

- **Loading**：浮层显示骨架屏（skeleton matching layout structure）
- **Error**：内联错误提示 + 重试按钮
- **Empty timeline**：右列显示"暂无动态记录"

## 7. Technical Notes

- 组件名：`StoreDetailModal.tsx`
- 放在 `frontend/components/StoreDetailModal.tsx`
- 使用 Next.js Portal（`next/navigation` 或 `createPortal`）渲染到 `document.body`
- 状态管理：父组件（`page.tsx`）持有 `selectedStoreId` state，传入 modal
- ESC 键关闭：useEffect 监听 `keydown` 事件
- 点击遮罩关闭：onClick on overlay div
- 响应式：移动端浮层占满屏幕（90vh, 100vw）

## 8. Implementation Order

1. 基础结构：StoreList 改为点击行触发 modal
2. Modal 基础：header + 关闭逻辑 + 骨架屏
3. 左侧：垂直步骤条 + 详情卡片
4. 右侧：动态时间线
5. MANUAL_REVIEW 状态 UI
6. Footer 操作按钮
7. 移动端适配 + polish
