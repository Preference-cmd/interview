"use client";

import { AgentRun, AGENT_LABELS } from "@/lib/types";
import { AlertTriangle } from "lucide-react";

interface FailureLogCardProps {
  recentAgentRuns: AgentRun[];
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function FailureLogCard({ recentAgentRuns }: FailureLogCardProps) {
  const failedRuns = recentAgentRuns
    .filter((r) => r.status === "failed")
    .slice(0, 3);

  if (failedRuns.length === 0) {
    return null;
  }

  return (
    <div className="bg-orange-50 rounded-comfortably-rounded border border-orange-200 p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center gap-2">
        <AlertTriangle className="size-4 text-orange-500 shrink-0" />
        <h4 className="text-[13px] font-semibold text-orange-700 font-anthropic-sans">
          最近失败详情
        </h4>
      </div>

      {/* Failure list */}
      <div className="flex flex-col gap-2">
        {failedRuns.map((run) => (
          <div
            key={run.id}
            className="bg-white/60 rounded-subtly-rounded border border-orange-200/50 p-3 flex flex-col gap-1.5"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] font-semibold text-orange-700">
                {AGENT_LABELS[run.agent_type] || run.agent_type}
              </span>
              <time className="text-[10px] text-orange-400 font-anthropic-mono">
                {formatTime(run.created_at)}
              </time>
            </div>
            <p className="text-[12px] text-charcoal-warm leading-relaxed line-clamp-2">
              {run.error_msg || "Unknown error"}
            </p>
            {run.duration_ms > 0 && (
              <span className="text-[10px] text-orange-400 font-anthropic-mono">
                {run.duration_ms}ms
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
