# Store Detail Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a comprehensive Store Detail Page (`/stores/[id]`) with a two-column layout, showing store info, workflow status, timeline, agent runs, and reports.

**Architecture:** Next.js App Router (client-side data fetching). The page is split into a fixed left panel (320px) and a flexible right panel. Uses shadcn/ui components customized to match the "Anthropic-inspired" design system (Parchment background, serif headers, warm grays).

**Tech Stack:** Next.js (TypeScript), shadcn/ui (Tailwind v4), Recharts (for KPI chart), Lucide (icons).

---

### Task 1: Setup Route & Shadcn Components

**Files:**
- Create: `frontend/app/stores/[id]/page.tsx`
- Modify: `frontend/package.json`

- [x] **Step 1: Install necessary shadcn components**
- [x] **Step 2: Create the dynamic route and basic layout**
- [x] **Step 3: Run dev server and verify route**
- [x] **Step 4: Commit**

---

### Task 2: Implement StoreInfoCard Component

**Files:**
- Create: `frontend/components/StoreInfoCard.tsx`
- Modify: `frontend/app/stores/[id]/page.tsx`

- [x] **Step 1: Create StoreInfoCard component using shadcn/ui**
- [x] **Step 2: Update Page to use StoreInfoCard**
- [x] **Step 3: Verify component renders correctly**
- [x] **Step 4: Commit**

---

### Task 3: Implement WorkflowStatusBar Component

**Files:**
- Create: `frontend/components/WorkflowStatusBar.tsx`

- [x] **Step 1: Implement WorkflowStatusBar**
- [x] **Step 2: Update Page to use WorkflowStatusBar**
- [x] **Step 3: Commit**

---

### Task 4: Implement VerticalTimeline Component

**Files:**
- Create: `frontend/components/VerticalTimeline.tsx`

- [x] **Step 1: Implement VerticalTimeline with expandable nodes**
- [x] **Step 2: Update Page to use VerticalTimeline**
- [x] **Step 3: Commit**

---

### Task 5: Agent Runs Table & Output Modal

**Files:**
- Create: `frontend/components/AgentRunsTable.tsx`

- [x] **Step 1: Implement AgentRunsTable using shadcn Table**
- [x] **Step 2: Implement Output Modal for viewing agent output JSON**
- [x] **Step 3: Commit**

---

### Task 6: KPI Line Chart & Finishing Touches

**Files:**
- Create: `frontend/components/KPILineChart.tsx`
- Create: `frontend/components/StoreDetailSkeleton.tsx`

- [ ] **Step 1: Implement KPILineChart using Recharts**

```tsx
// frontend/components/KPILineChart.tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

// Mock data generator or derived from extra_data
const data = [
  { name: 'Mon', gmv: 4000, orders: 240, rating: 4.2 },
  { name: 'Tue', gmv: 3000, orders: 139, rating: 4.1 },
  // ...
];

export function KPILineChart() {
  return (
    <div className="h-full flex flex-col gap-4">
      <Tabs defaultValue="gmv" className="w-full">
        <TabsList className="bg-parchment/50 border-none h-8 p-1">
          <TabsTrigger value="gmv" className="text-[10px] uppercase h-6">GMV</TabsTrigger>
          <TabsTrigger value="orders" className="text-[10px] uppercase h-6">Orders</TabsTrigger>
          <TabsTrigger value="rating" className="text-[10px] uppercase h-6">Rating</TabsTrigger>
        </TabsList>
      </Tabs>
      <div className="flex-1 min-h-[160px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0eee6" />
            <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#87867f' }} />
            <Tooltip contentStyle={{ backgroundColor: '#faf9f5', border: '1px solid #f0eee6', borderRadius: '8px' }} />
            <Line type="monotone" dataKey="gmv" stroke="#c96442" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Implement Loading Skeleton**

- [ ] **Step 3: Final Page integration and styling polish**

- [ ] **Step 4: Commit**
