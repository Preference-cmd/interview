import { AgentRun, AGENT_LABELS, AGENT_COLORS } from "@/lib/types";
import { Clock, CheckCircle2, XCircle, AlertTriangle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface StoreTimelineProps {
  events: any[];
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

function EventIcon({ type, agentType }: { type: string; agentType?: string | null }) {
  if (type === "state_change") {
    return <div className="size-2.5 rounded-full bg-focus-blue shrink-0 mt-1" />;
  }
  if (type === "agent_run") {
    const color = AGENT_COLORS[agentType || ""] || "#6b7280";
    return <div className="size-2.5 rounded-full shrink-0 mt-1" style={{ background: color }} />;
  }
  if (type === "manual_takeover") {
    return <AlertTriangle className="size-3 text-terracotta shrink-0 mt-1" />;
  }
  if (type === "report_generated") {
    return <CheckCircle2 className="size-3 text-olive-gray shrink-0 mt-1" />;
  }
  return <Clock className="size-3 text-stone-gray shrink-0 mt-1" />;
}

const EVENT_TYPE_LABELS: Record<string, string> = {
  state_change: "状态变更",
  agent_run: "Agent 执行",
  workflow_created: "工作流创建",
  manual_takeover: "人工接管",
  report_generated: "报表生成",
};

export function StoreTimeline({ events }: StoreTimelineProps) {
  if (events.length === 0) {
    return (
      <div className="p-12 text-center text-stone-gray">
        暂无事件记录
      </div>
    );
  }

  return (
    <div className="relative pl-6">
      <div className="absolute left-1.5 top-2 bottom-2 w-px bg-border-cream" />
      <div className="flex flex-col gap-6">
        {events.map((event) => (
          <div
            key={event.id}
            className="relative group"
          >
            <div className="absolute -left-[24.5px] top-0 flex items-start justify-center w-4 h-full">
               <EventIcon type={event.event_type} agentType={event.agent_type} />
            </div>
            
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-sm font-semibold text-anthropic-near-black">
                  {EVENT_TYPE_LABELS[event.event_type] || event.event_type}
                </span>
                {event.agent_type && (
                  <span className="text-[11px] px-2 py-0.5 rounded-sharp bg-warm-sand text-charcoal-warm font-medium">
                    {AGENT_LABELS[event.agent_type] || event.agent_type}
                  </span>
                )}
                {event.from_state && event.to_state && (
                  <span className="text-[11px] text-stone-gray font-anthropic-mono">
                    {event.from_state} → {event.to_state}
                  </span>
                )}
              </div>
              
              {event.message && (
                <p className="text-[13px] text-olive-gray leading-relaxed m-0">
                  {event.message}
                </p>
              )}
              
              <time className="text-[11px] text-stone-gray font-anthropic-mono">
                {formatTime(event.created_at)}
              </time>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
