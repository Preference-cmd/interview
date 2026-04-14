"use client";

import { Store, AgentRun, AGENT_LABELS, AGENT_COLORS } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

interface StepDetailCardProps {
  state: string;
  store: Store;
  recentAgentRuns?: AgentRun[];
}

const STATE_CONFIG: Record<
  string,
  {
    title: string;
    statusLabel: string;
    description: string;
    agents: string[];
    metrics: { key: keyof Store; label: string; warning?: (v: number) => boolean }[];
  }
> = {
  NEW_STORE: {
    title: "New Store",
    statusLabel: "Waiting",
    description: "门店已导入，等待启动工作流",
    agents: [],
    metrics: [],
  },
  DIAGNOSIS: {
    title: "Health Diagnosis",
    statusLabel: "In Progress",
    description: "对门店进行全面健康检查与数据分析",
    agents: ["analyzer"],
    metrics: [
      { key: "rating", label: "Rating" },
      { key: "review_count", label: "Reviews" },
      { key: "review_reply_rate", label: "Reply Rate", warning: (v) => v < 0.5 },
      { key: "monthly_orders", label: "Monthly Orders" },
    ],
  },
  FOUNDATION: {
    title: "Infrastructure",
    statusLabel: "In Progress",
    description: "完善门店信息，优化展示与评分",
    agents: ["web_operator", "mobile_operator"],
    metrics: [
      { key: "rating", label: "Rating" },
      { key: "competitor_avg_discount", label: "Competitor Discount" },
      { key: "review_count", label: "Reviews" },
      { key: "gmv_last_7d", label: "7D GMV" },
    ],
  },
  DAILY_OPS: {
    title: "Daily Operations",
    statusLabel: "In Progress",
    description: "日常运营自动化：评价回复、订单监控",
    agents: ["analyzer", "web_operator", "mobile_operator", "reporter"],
    metrics: [
      { key: "gmv_last_7d", label: "7D GMV" },
      { key: "monthly_orders", label: "Monthly Orders" },
      { key: "review_reply_rate", label: "Reply Rate", warning: (v) => v < 0.5 },
      { key: "review_count", label: "Reviews" },
    ],
  },
  WEEKLY_REPORT: {
    title: "Weekly Report",
    statusLabel: "In Progress",
    description: "生成周报与数据分析报告",
    agents: ["reporter"],
    metrics: [
      { key: "gmv_last_7d", label: "7D GMV" },
      { key: "monthly_orders", label: "Monthly Orders" },
      { key: "review_count", label: "Reviews" },
      { key: "review_reply_rate", label: "Reply Rate", warning: (v) => v < 0.5 },
    ],
  },
  DONE: {
    title: "Completed",
    statusLabel: "Done",
    description: "工作流已完成",
    agents: [],
    metrics: [
      { key: "gmv_last_7d", label: "7D GMV" },
      { key: "monthly_orders", label: "Monthly Orders" },
      { key: "rating", label: "Rating" },
      { key: "review_count", label: "Reviews" },
    ],
  },
  MANUAL_REVIEW: {
    title: "Manual Review",
    statusLabel: "Blocked",
    description: "需要人工介入处理异常",
    agents: [],
    metrics: [
      { key: "gmv_last_7d", label: "7D GMV" },
      { key: "monthly_orders", label: "Monthly Orders" },
      { key: "rating", label: "Rating" },
      { key: "review_count", label: "Reviews" },
    ],
  },
};

function MetricCell({
  label,
  value,
  warning,
}: {
  label: string;
  value: number | string;
  warning?: boolean;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[11px] text-stone-gray font-anthropic-sans">
        {label}
      </span>
      <span
        className={cn(
          "text-[18px] font-medium font-anthropic-serif leading-tight",
          warning ? "text-orange-500" : "text-anthropic-near-black"
        )}
      >
        {typeof value === "number" ? (
          value.toLocaleString("zh-CN")
        ) : (
          value
        )}
      </span>
    </div>
  );
}

export function StepDetailCard({
  state,
  store,
  recentAgentRuns = [],
}: StepDetailCardProps) {
  const config =
    STATE_CONFIG[state] || STATE_CONFIG["NEW_STORE"];

  const statusBadgeClass = cn(
    "inline-block rounded-full px-2.5 py-0.5 text-[11px] font-semibold",
    config.statusLabel === "Done" &&
      "bg-green-100 text-green-700 border border-green-200",
    config.statusLabel === "Waiting" &&
      "bg-warm-sand text-stone-gray border border-border-warm",
    config.statusLabel === "Blocked" &&
      "bg-red-100 text-error-crimson border border-red-200",
    config.statusLabel === "In Progress" &&
      "bg-terracotta/10 text-terracotta border border-terracotta/20"
  );

  return (
    <div className="bg-ivory rounded-comfortably-rounded border border-border-cream shadow-whisper p-5 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="font-anthropic-serif text-[16px] font-medium text-anthropic-near-black">
          {config.title}
        </h3>
        <span className={statusBadgeClass}>{config.statusLabel}</span>
      </div>

      {/* Description */}
      <p className="text-[13px] text-olive-gray leading-relaxed">
        {config.description}
      </p>

      {/* Agent tags */}
      {config.agents.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {config.agents.map((agent) => (
            <span
              key={agent}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-subtly-rounded text-[11px] font-medium bg-warm-sand border border-border-warm text-charcoal-warm"
              style={{
                borderLeft: `3px solid ${AGENT_COLORS[agent] || "#87867f"}`,
              }}
            >
              <span
                className="size-1.5 rounded-full shrink-0"
                style={{ backgroundColor: AGENT_COLORS[agent] || "#87867f" }}
              />
              {AGENT_LABELS[agent] || agent}
            </span>
          ))}
        </div>
      )}

      {/* 2x2 Metrics grid */}
      {config.metrics.length > 0 && (
        <div className="grid grid-cols-2 gap-4">
          {config.metrics.map((metric) => {
            const rawValue = store[metric.key];
            const numValue = typeof rawValue === "number" ? rawValue : 0;
            const isWarning = metric.warning ? metric.warning(numValue) : false;

            return (
              <MetricCell
                key={metric.key}
                label={metric.label}
                value={numValue}
                warning={isWarning}
              />
            );
          })}
        </div>
      )}

      {/* Issue tags */}
      {store.issues && store.issues.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1 border-t border-border-cream">
          {store.issues.map((issue, i) => (
            <Badge
              key={i}
              variant="destructive"
              className="text-[10px] font-medium px-2 py-0.5"
            >
              {issue}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
