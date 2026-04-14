# Store Detail Page — Design Specification

## Status: MVP

## 1. Overview

Add a dedicated store detail page (`/stores/[id]`) to the existing Next.js App Router SPA. This fills the most critical UX gap: users currently cannot inspect a single store's workflow progress, timeline, or agent run history without a dedicated view.

## 2. Routing & Navigation

- **Route**: `/stores/[id]` (Next.js App Router dynamic route)
- **Entry point**: Click on any store row in the store list page (`/stores`)
- **Back navigation**: Breadcrumb "← Back to Store List" at the top
- **No route guards needed**: data fetched client-side via API

## 3. Page Layout — Two-Column Split

```
┌──────────────────────────────────────────────────────┐
│  ← Back to Store List      [Manual Takeover Button]  │
│                                                      │
│  Store Name / 评分 / 城市 / 状态徽章                   │
├──────────────────────┬───────────────────────────────┤
│  LEFT PANEL (320px)  │  RIGHT PANEL (flex-1)        │
│                      │                               │
│  ┌────────────────┐ │  Workflow Status Bar         │
│  │ Basic Info Card │ │  ─────────────────────────   │
│  └────────────────┘ │                               │
│                      │  Vertical Timeline            │
│  ┌────────────────┐ │  (scrollable)                │
│  │ KPI Metric Cards│ │                               │
│  └────────────────┘ │                               │
│                      │  Agent Runs Table             │
│  ┌────────────────┐ │                               │
│  │ KPI Line Chart │ │  Report Preview                │
│  └────────────────┘ │                               │
└──────────────────────┴───────────────────────────────┘
```

- Left panel: fixed 320px width, scrolls independently if content overflows
- Right panel: flexible width, independent vertical scroll
- Page max-width: 1200px, centered

## 4. Left Panel — Store Information

### 4.1 Header Bar (above two-column split)

- "← Back to Store List" text link in Olive Gray, hover → Near Black
- Store name in Anthropic Serif 36px
- Metadata row: city, category, star rating (★ icon), StateBadge component
- Manual Takeover button (right-aligned in header bar): Terracotta background, Ivory text, 12px radius

### 4.2 Basic Info Card

Background: Ivory (#faf9f5), border: 1px solid Border Cream (#f0eee6), radius: 16px, padding: 24px, whisper shadow.

Fields displayed:
- **City** — from `store.city`
- **Category** — from `store.category`
- **Rating** — ★ icon (gold if ≥ 3.5, crimson if < 3.5) + numeric value
- **ROS Health** — StateBadge with color coding: green/amber/red
- **GMV (7d)** — from `store.gmv_last_7d`, formatted with ¥
- **Monthly Orders** — from `store.monthly_orders`, formatted with comma
- **Review Count** — from `store.review_count`
- **Review Reply Rate** — percentage
- **Competitor Avg Discount** — from `store.competitor_avg_discount`
- **Issues** — list of issue strings, shown as small amber badges

### 4.3 KPI Line Chart

Below the info card, stacked vertically.

- **Library**: recharts (already in use by DashboardCharts)
- **Metric selector**: small pill tabs above the chart — "GMV", "Orders", "Rating", "Reply Rate"
- **Data**: mock 7-day trend data derived from `gmv_last_7d` and other available fields
- **Chart style**: warm color palette matching design system (no blue/green chart defaults), terracotta accent line, cream grid lines
- **Height**: ~200px

### 4.4 Manual Takeover Button

- Full width of left panel
- Background: Error Crimson (#b53333), text Ivory (#faf9f5)
- Label: "Manual Takeover"
- Calls `POST /stores/{id}/manual-takeover`
- Shows loading spinner while pending, then success toast
- Only shown when store state is `MANUAL_REVIEW` (or always visible, configurable)

## 5. Right Panel — Workflow & Activity

### 5.1 Workflow Status Bar

Horizontal step indicator showing all 6 states:

```
[NEW_STORE] → [DIAGNOSIS] → [FOUNDATION] → [DAILY_OPS] → [WEEKLY_REPORT] → [DONE]
                  ↓
            [MANUAL_REVIEW] ← error branch
```

- Current state: Terracotta background, Ivory text
- Completed states: filled circle checkmark, Olive Gray text
- Pending states: empty circle, Stone Gray text
- Error/exception branch: separate row below with warning icon

Fetched from `GET /stores/{id}/status`.

### 5.2 Vertical Timeline

- Left vertical line connecting nodes (Border Warm color)
- Each node: circle icon (different icon per event type) + content block
- Content block per node:
  - **Event type icon** (different for: state_change, agent_run, report_generated, manual_takeover)
  - **Description text** — the `message` field from event log
  - **Agent type badge** — warm sand pill (only shown for agent_run events)
  - **Duration** — in ms, shown for agent_run events
  - **Timestamp** — relative time ("2h ago") + absolute on hover
  - **Expand toggle** — chevron, expands to show `extra_data` JSON in a small code block
- Scrollable container, newest events at top

Fetched from `GET /stores/{id}/timeline`.

### 5.3 Agent Runs Table

Below the timeline, separated by a section header "Agent Execution History".

- Columns: Type | Status | Duration | Timestamp | Actions
- **Type**: badge pills (Diagnosis / Backend / Mobile / Report)
- **Status**: colored text — "Success" in Olive Gray, "Failed" in Error Crimson, "Running" in Terracotta
- **Duration**: in ms, mono font
- **Timestamp**: relative time
- **Actions**: "View Output" button — opens a small modal/drawer showing `output_data` JSON
- Alternating row backgrounds using parchment/ivory

Fetched from `GET /stores/{id}/status` (recent_agent_runs array).

### 5.4 Report Preview

Section header "Generated Reports".

- Lists recent reports from `GET /stores/{id}` (reports array)
- Each report item: report type badge (Daily/Weekly), generation timestamp, collapsible markdown body
- Markdown rendered with a simple stylesheet (no heavy library — just basic styling for headings, lists, tables)
- If no reports: "No reports generated yet" in Stone Gray italic

## 6. API Calls on Page Load

All calls in parallel via `Promise.all`:

| Call | Endpoint | Used For |
|------|----------|----------|
| `getStore(id)` | `GET /stores/{id}` | Info card, reports |
| `getStatus(id)` | `GET /stores/{id}/status` | Workflow state, agent runs |
| `getTimeline(id)` | `GET /stores/{id}/timeline` | Vertical timeline events |

## 7. Loading & Error States

- **Loading**: skeleton placeholders matching the layout structure (shimmer animation)
- **Error**: inline error message with retry button
- **Empty timeline**: "No events yet" placeholder

## 8. Design System Compliance

All components must follow `frontend/DESIGN.md`:

- Colors: warm palette only — no cool blue-grays
- Typography: Anthropic Serif for headings, Anthropic Sans for UI, Anthropic Mono for code/timestamps
- Border radius: 8px (comfortably rounded) for cards, 12px for buttons
- Shadows: whisper shadow for cards (`0px 4px 24px rgba(0,0,0,0.05)`)
- Ring-based borders for interactive elements

## 9. Responsive Behavior

- **< 768px (mobile)**: left and right panels stack vertically, left panel on top
- **768px+ (tablet/desktop)**: two-column layout

## 10. Components to Create

1. `frontend/app/stores/[id]/page.tsx` — main page component
2. `frontend/components/StoreInfoCard.tsx` — left panel info card
3. `frontend/components/WorkflowStatusBar.tsx` — horizontal step indicator
4. `frontend/components/VerticalTimeline.tsx` — timeline with expandable nodes
5. `frontend/components/AgentRunsTable.tsx` — runs table with output modal
6. `frontend/components/ReportPreview.tsx` — markdown report renderer
7. `frontend/components/KPILineChart.tsx` — recharts line chart for KPI trends
8. `frontend/components/StoreDetailSkeleton.tsx` — loading skeleton

## 11. Milestones

### Phase 1: Core Detail View
- Route + layout scaffolding
- Basic info card
- Workflow status bar
- Vertical timeline (simple version)

### Phase 2: Data Tables
- Agent runs table with output modal
- Report preview with markdown rendering

### Phase 3: KPI Charts & Polish
- KPI line chart with metric selector
- Loading skeletons
- Error states
- Responsive layout

## 12. Open Questions (Deferred)

- Mock 7-day KPI trend data — where does it come from? (StoreTimeline component has historical data in `extra_data`?)
- Report markdown rendering library — use `react-markdown` or basic HTML?
- Manual Takeover button visibility — always shown or only in `MANUAL_REVIEW` state?
