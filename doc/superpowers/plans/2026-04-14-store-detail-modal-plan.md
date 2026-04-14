# Store Detail Modal — Implementation Plan

**Date:** 2026-04-14
**Status:** Implementation Plan
**Phase:** Store Detail Modal
**Files Referenced:**
- Design spec: `doc/superpowers/specs/STORE-DETAIL-DESIGN.md`
- Existing components: `frontend/components/StoreList.tsx`, `frontend/components/StoreTimeline.tsx`, `frontend/components/VerticalTimeline.tsx`, `frontend/components/WorkflowStatusBar.tsx`, `frontend/components/StoreInfoCard.tsx`, `frontend/components/StoreDetailSkeleton.tsx`
- API: `frontend/lib/api.ts`
- Types: `frontend/lib/types.ts`
- UI primitives: `frontend/components/ui/dialog.tsx`, `frontend/components/ui/scroll-area.tsx`, `frontend/components/ui/badge.tsx`

---

## 1. Overview

Implement a modal overlay triggered by clicking any row in the Store List table. The modal shows store workflow details on the left and recent activity timeline on the right. The modal uses the existing shadcn/ui `Dialog` primitive for accessibility (ESC, backdrop click, focus trap built-in).

### Design System Notes

- **Colors:** Tailwind v4 CSS variables — `parchment`, `ivory`, `terracotta`, `border-cream`, etc.
- **Typography:** `font-anthropic-serif` for headlines, `font-anthropic-sans` for UI text, `font-anthropic-mono` for metadata
- **Radius:** `rounded-comfortably-rounded` (8px) for cards, `rounded-generously-rounded` (12px) for buttons
- **Shadows:** `shadow-whisper` for elevated cards
- **Radix primitives:** Use `Dialog`, `ScrollArea` from shadcn/ui

### Key Existing Components to Reuse/Extend

| Component | Use |
|-----------|-----|
| `StateBadge.tsx` | Header and step indicators |
| `VerticalTimeline.tsx` | Right column activity timeline (nearly matches spec — event colors, icon nodes, expand/collapse) |
| `StoreDetailSkeleton.tsx` | Loading skeleton (but designed for a full page layout, needs adaptation for modal) |
| `StoreInfoCard.tsx` | Reference for metrics/issue styling in the detail card |
| `WorkflowStatusBar.tsx` | **Horizontal** stepper — spec requires **vertical** stepper. Create new `WorkflowStepper.tsx` (vertical). |

---

## 2. Files to Create / Modify

### Create

| File | Purpose |
|------|---------|
| `frontend/components/WorkflowStepper.tsx` | Vertical 6-step workflow indicator (new — existing `WorkflowStatusBar` is horizontal) |
| `frontend/components/StoreDetailModal.tsx` | Main modal component — header, left column, right column, footer, all state variants |
| `frontend/components/StepDetailCard.tsx` | Current step detail card with metrics grid and issue tags |
| `frontend/components/FailureLogCard.tsx` | Orange failure log card for MANUAL_REVIEW state |

### Modify

| File | Change |
|------|--------|
| `frontend/components/StoreList.tsx` | Add `onSelectStore` prop; wrap each `<tr>` with click handler + cursor pointer; remove existing "Start" button (moved to modal footer) |
| `frontend/app/page.tsx` | Lift `selectedStoreId` state; render `<StoreDetailModal>` when set; pass handlers for close/continue/retry |

---

## 3. Task Breakdown

### Task 1: Create WorkflowStepper (vertical)

**Files:** `frontend/components/WorkflowStepper.tsx`

Create a vertical stepper component for the left column. Spec requirements:

- 6 steps: `NEW_STORE → DIAGNOSIS → FOUNDATION → DAILY_OPS → WEEKLY_REPORT → DONE`
- Step styles:
  - **Completed:** green fill + checkmark icon
  - **Current:** terracotta fill + step number + outer glow (`shadow-[0_0_10px_rgba(201,100,66,0.3)]`)
  - **Pending:** gray outline, empty
  - **MANUAL_REVIEW:** red outline + exclamation icon, rendered as separate row below the 6 steps (not inline)
- Each step shows: circle node + step label (English) + Chinese subtitle
- Steps connected by vertical line

```tsx
interface WorkflowStepperProps {
  currentState: string;
}
```

**State to Chinese subtitle mapping:**
```
NEW_STORE: "新建门店"
DIAGNOSIS: "健康诊断"
FOUNDATION: "基础建设"
DAILY_OPS: "日常运营"
WEEKLY_REPORT: "周报生成"
DONE: "已完成"
MANUAL_REVIEW: "人工介入"
```

### Task 2: Create StepDetailCard

**Files:** `frontend/components/StepDetailCard.tsx`

Current step detail card shown below the stepper. Content varies by state:

- **Header:** Step title + status tag ("进行中" / "已完成" / "等待处理")
- **Description:** State-specific description text (hardcoded per state)
- **Agent tags:** Show relevant agents for the current state (e.g., DIAGNOSIS shows Analyzer Agent)
- **2x2 Metrics grid:** Rating, Monthly Orders, 7D GMV, Reply Rate
  - Values come from `Store` fields: `rating`, `monthly_orders`, `gmv_last_7d`, `review_reply_rate`
  - Threshold coloring: rating < 3.5 = red, reply_rate < 0.5 = orange, etc.
- **Issue tags:** Red badges from `store.issues` array

**State-specific content:**

| State | Description | Agents | Metrics |
|-------|-------------|--------|---------|
| NEW_STORE | 门店已导入，等待启动工作流 | — | — |
| DIAGNOSIS | 对门店进行全面健康检查与数据分析 | analyzer | rating, review_count, reply_rate, monthly_orders |
| FOUNDATION | 完善门店信息，优化展示与评分 | web_operator, mobile_operator | rating, competitor_avg_discount, review_count, gmv_last_7d |
| DAILY_OPS | 日常运营自动化：评价回复、订单监控 | all agents | gmv_last_7d, monthly_orders, review_reply_rate, review_count |
| WEEKLY_REPORT | 生成周报与数据分析报告 | reporter | gmv_last_7d, monthly_orders, review_count, reply_rate |
| DONE | 工作流已完成 | — | — |
| MANUAL_REVIEW | 需要人工介入处理异常 | — | — |

```tsx
interface StepDetailCardProps {
  state: string;
  store: Store;
}
```

### Task 3: Create FailureLogCard

**Files:** `frontend/components/FailureLogCard.tsx`

Orange failure log card visible only in MANUAL_REVIEW state. Per spec:

- Background: `bg-orange-50` (#fff7ed — close to spec's `#fff7ed`)
- Border: `border border-orange-200`
- Title: "最近失败详情" with warning icon
- Shows last 3 failed agent runs: timestamp + error message
- Data from `WorkflowStatus.recent_agent_runs` filtered by `status === "failed"`, sorted newest first

```tsx
interface FailureLogCardProps {
  recentAgentRuns: AgentRun[];
}
```

### Task 4: Create StoreDetailModal (main component)

**Files:** `frontend/components/StoreDetailModal.tsx`

Main modal using Radix `Dialog` primitive. Layout per spec:

**Header:**
- Left: Store avatar (44x44, terracotta bg + first char of name), store name (18px Anthropic Serif bold), metadata line (`城市 · 类目 · store_id · 评分`)
- Right: StateBadge, action buttons (Manual Takeover if not in MANUAL_REVIEW, Start/Retry if in MANUAL_REVIEW), close button (X icon)
- Action buttons call `manualTakeover()` and `startWorkflow()` from `api.ts`

**Left Column (flex: 1):**
- Section label: "工作流进度"
- `<WorkflowStepper>` component
- `<StepDetailCard>` component
- `<FailureLogCard>` (conditional, only when state === MANUAL_REVIEW)

**Right Column (flex: 1):**
- Section label: "近期动态"
- `<VerticalTimeline>` component with events sorted newest-first
- Empty state: "暂无动态记录"

**Footer:**
- Left: "关闭" button (secondary)
- Right: "继续下一步" button (terracotta primary, calls `startWorkflow()`)

**Data fetching:**
On modal open (when `storeId` is set), parallel fetch:
```ts
const [store, status, events] = await Promise.all([
  getStore(storeId),
  getStatus(storeId),
  getTimeline(storeId),
]);
```

**Loading state:** Show skeleton matching modal layout structure (adapt from existing `StoreDetailSkeleton.tsx` — the existing skeleton is for a full page, so create a simpler inline skeleton or overlay skeleton for the modal).

**Error state:** Show inline error with retry button.

**Props:**
```tsx
interface StoreDetailModalProps {
  storeId: number | null;       // null = closed
  onClose: () => void;
  onWorkflowStarted: () => void; // callback to refresh parent data
}
```

**Keyboard/Accessibility:**
- ESC closes (Dialog primitive handles this)
- Backdrop click closes (Dialog primitive handles this)
- Focus trap is built into Dialog primitive
- `aria-label` on close button, proper heading hierarchy

### Task 5: Integrate into StoreList

**Files:** `frontend/components/StoreList.tsx`

1. Add `onSelectStore: (storeId: number) => void` prop to `StoreListProps`
2. Change `<tr>` onClick to call `onSelectStore(store.id)` — **remove** the existing "Start" button action from the row
3. Add `cursor-pointer` and `hover:bg-parchment/50` to the `<tr>` for visual affordance
4. Keep the row's action cell clean (Start button removed since it's in the modal footer now)

### Task 6: Integrate into page.tsx

**Files:** `frontend/app/page.tsx`

1. Add `selectedStoreId` state: `useState<number | null>(null)`
2. Add `refreshTrigger` state to force StoreList re-render after modal actions
3. Render `<StoreDetailModal>` when `selectedStoreId !== null`:
   ```tsx
   {selectedStoreId !== null && (
     <StoreDetailModal
       storeId={selectedStoreId}
       onClose={() => setSelectedStoreId(null)}
       onWorkflowStarted={() => {
         setSelectedStoreId(null);
         setRefreshTrigger(n => n + 1);
       }}
     />
   )}
   ```
4. Pass `onSelectStore={setSelectedStoreId}` to `<StoreList>`
5. Add `refreshTrigger` to the `useEffect` dependency array for `loadData`

---

## 4. Implementation Order

```
Wave 1 (Tasks 1, 2, 3 — can be parallel)
  Task 1: WorkflowStepper.tsx (vertical stepper)
  Task 2: StepDetailCard.tsx (current step detail)
  Task 3: FailureLogCard.tsx (MANUAL_REVIEW failure log)

Wave 2 (Task 4 depends on 1-3)
  Task 4: StoreDetailModal.tsx (main component wiring all sub-components)

Wave 3 (Tasks 5, 6 — integration)
  Task 5: Modify StoreList.tsx (add click handler)
  Task 6: Modify page.tsx (lift state, render modal)
```

---

## 5. Verification

After each task:

| Task | Verify |
|------|--------|
| Task 1 | `WorkflowStepper` renders all 6 steps + MANUAL_REVIEW row; step styles match spec |
| Task 2 | `StepDetailCard` shows correct agents/metrics per state; issue tags render |
| Task 3 | `FailureLogCard` appears only when failed agent runs exist; orange styling matches spec |
| Task 4 | Modal opens on row click; all 7 state variants render correctly; close works via ESC/backdrop/X |
| Task 5 | StoreList rows are clickable; no Start button in action cell |
| Task 6 | Full flow: click row → modal opens → close → click another row → modal opens |

**Manual verification checklist:**
1. Open a store in NEW_STORE state — stepper shows all gray, detail card shows "尚未启动"
2. Open a store in DIAGNOSIS — step 2 terracotta highlighted, Analyzer Agent tag shown
3. Open a store in MANUAL_REVIEW — red ! step shown, failure log card visible with orange styling
4. Click Start/Continue button in modal footer — workflow starts, modal can be closed
5. Click Manual Takeover — action completes
6. Close with ESC, backdrop click, and X button — all work
7. Mobile viewport — modal fills screen (Dialog primitive handles max-width)

---

## 6. Concerns and Questions

### CONCERN 1: API response shape for metrics

**Issue:** The `StepDetailCard` 2x2 metrics grid needs `monthly_orders`, `gmv_last_7d`, `review_reply_rate`, `review_count`. These exist on the `Store` type (from `getStore()`), which is correct. However, `WorkflowStatus` also has `recent_agent_runs` with `output_data` that may contain per-state metrics.

**Resolution:** Use `Store` fields for the 2x2 grid (from `getStore()` response). Use `WorkflowStatus.recent_agent_runs` only for the failure log and agent tags.

### CONCERN 2: Existing WorkflowStatusBar is horizontal, spec requires vertical

**Resolution:** Create a new `WorkflowStepper.tsx` (vertical). Do NOT modify the existing `WorkflowStatusBar.tsx` (it's used elsewhere or may be referenced). Keep them separate.

### CONCERN 3: Failure log data — recent_agent_runs vs event logs

**Issue:** The spec says "列出最近 3 次失败：时间戳 + 错误信息". `WorkflowStatus.recent_agent_runs` provides this with `error_msg` field. `EventLog` also has agent run events but may not include the full error message.

**Resolution:** Use `WorkflowStatus.recent_agent_runs.filter(r => r.status === 'failed').slice(0, 3)` for the failure log card. This is fetched via `getStatus()` which is already part of the parallel fetch.

### CONCERN 4: StoreDetailSkeleton designed for full page, not modal

**Resolution:** Create the skeleton inline within `StoreDetailModal.tsx` using `cn`-merged placeholder divs with `bg-warm-sand/50` and `animate-pulse`. Do not import the existing `StoreDetailSkeleton.tsx` (it has a full-page header structure incompatible with a modal overlay).

### CONCERN 5: VerticalTimeline is nearly identical to StoreTimeline

**Resolution:** The existing `VerticalTimeline.tsx` already implements most of the spec requirements for the right column timeline. Use it directly with `events={events}` where events are the `EventLog[]` from `getTimeline()`. The existing `StoreTimeline.tsx` can be considered deprecated or used elsewhere.

### CONCERN 6: Tailwind v4 CSS variable naming

**Resolution:** Use the CSS variable names directly as Tailwind utilities:
- `text-parchment` (doesn't exist as a utility) — use `text-[#f5f4ed]` or add to theme
- `bg-warm-sand` — exists as utility
- `border-border-cream` — exists as utility
- For colors not mapped: use inline styles or `text-[#hex]`

Note: The existing codebase uses `bg-warm-sand`, `border-border-cream`, etc. as utilities. Some colors like `parchment` text aren't used, so fallback to `text-[#hex]` where needed.

### CONCERN 7: Modal backdrop and scroll locking

**Resolution:** Radix `Dialog` from shadcn/ui handles `aria-hidden` on the rest of the page and prevents body scroll. The overlay (`bg-black/80 backdrop-blur`) is defined in the existing `DialogOverlay`. The modal content should use `ScrollArea` from shadcn/ui for the right column timeline to prevent internal scroll issues.

---

## 7. Output

After implementation, update `doc/STATE.md` to mark the Store Detail Modal feature as complete.
