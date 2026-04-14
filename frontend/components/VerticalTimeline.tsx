"use client";

import React, { useState } from "react";
import { 
  Activity, 
  Cpu, 
  FileText, 
  UserCog, 
  ChevronDown, 
  ChevronUp, 
  Clock 
} from "lucide-react";
import { EventLog, AGENT_COLORS, AGENT_LABELS } from "@/lib/types";
import { cn, getRelativeTime } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface VerticalTimelineProps {
  events: EventLog[];
  className?: string;
}

export function VerticalTimeline({ events, className }: VerticalTimelineProps) {
  const [expandedEvents, setExpandedEvents] = useState<Set<number>>(new Set());

  const toggleExpand = (id: number) => {
    const newExpanded = new Set(expandedEvents);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedEvents(newExpanded);
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case "state_change":
        return <Activity className="size-3.5" aria-hidden="true" />;
      case "agent_run":
        return <Cpu className="size-3.5" aria-hidden="true" />;
      case "report_generated":
        return <FileText className="size-3.5" aria-hidden="true" />;
      case "manual_takeover":
        return <UserCog className="size-3.5" aria-hidden="true" />;
      default:
        return <Activity className="size-3.5" aria-hidden="true" />;
    }
  };

  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-stone-gray/50 italic font-serif">
        <Clock className="size-8 mb-2 opacity-20" aria-hidden="true" />
        <p>No activity recorded yet</p>
      </div>
    );
  }

  return (
    <div className={cn("relative pb-8", className)}>
      {/* Vertical Connector Line */}
      <div 
        className="absolute left-3 top-2 bottom-0 w-0.5 bg-border-warm" 
        aria-hidden="true" 
      />

      <div className="space-y-8">
        {events.map((event) => {
          const isExpanded = expandedEvents.has(event.id);
          const hasExtraData = event.extra_data && Object.keys(event.extra_data).length > 0;

          return (
            <div key={event.id} className="relative pl-10">
              {/* Icon Node */}
              <div 
                className={cn(
                  "absolute left-0 top-1 size-6 rounded-full border-2 border-border-warm bg-ivory flex items-center justify-center z-10 shadow-sm",
                  event.event_type === "manual_takeover" ? "text-error-crimson" : "text-olive-gray"
                )}
              >
                {getEventIcon(event.event_type)}
              </div>

              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-anthropic-near-black">
                      {event.message}
                    </span>
                    
                    {event.event_type === "agent_run" && event.agent_type && (
                      <Badge 
                        variant="secondary" 
                        className="text-[10px] uppercase tracking-wider font-mono py-0 h-4 bg-warm-sand border-border-warm text-stone-gray"
                        style={{ 
                          borderLeft: `3px solid ${AGENT_COLORS[event.agent_type] || '#87867f'}` 
                        }}
                      >
                        {AGENT_LABELS[event.agent_type] || event.agent_type}
                      </Badge>
                    )}

                    {event.event_type === "agent_run" && event.extra_data?.duration_ms && (
                      <span className="text-[10px] text-stone-gray font-mono">
                        {event.extra_data.duration_ms}ms
                      </span>
                    )}

                    {event.event_type === "state_change" && event.from_state && event.to_state && (
                      <div className="flex items-center gap-1.5 text-[10px] font-mono text-stone-gray">
                        <span className="opacity-60">{event.from_state}</span>
                        <span className="opacity-30">→</span>
                        <span className="font-bold text-olive-gray">{event.to_state}</span>
                      </div>
                    )}
                  </div>
                  
                  <span 
                    className="text-[10px] text-stone-gray font-mono whitespace-nowrap cursor-help"
                    title={new Date(event.created_at).toLocaleString()}
                  >
                    {getRelativeTime(event.created_at)}
                  </span>
                </div>

                {hasExtraData && (
                  <div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleExpand(event.id)}
                      aria-expanded={isExpanded}
                      className="h-6 px-1 text-[10px] text-stone-gray hover:text-anthropic-near-black hover:bg-parchment gap-1 -ml-1"
                    >
                      {isExpanded ? (
                        <>
                          <ChevronUp className="size-3" aria-hidden="true" />
                          Hide Details
                        </>
                      ) : (
                        <>
                          <ChevronDown className="size-3" aria-hidden="true" />
                          View Data
                        </>
                      )}
                    </Button>

                    {isExpanded && (
                      <div className="mt-2 rounded-subtly-rounded border border-border-warm bg-parchment overflow-hidden">
                        <pre className="p-3 text-[11px] font-mono text-olive-gray overflow-x-auto max-h-[300px] scrollbar-thin scrollbar-thumb-border-warm">
                          {JSON.stringify(event.extra_data, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
