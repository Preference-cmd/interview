"use client";

import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { StateBadge } from "@/components/StateBadge";
import { WorkflowStepper } from "@/components/WorkflowStepper";
import { StepDetailCard } from "@/components/StepDetailCard";
import { FailureLogCard } from "@/components/FailureLogCard";
import { VerticalTimeline } from "@/components/VerticalTimeline";
import {
  getStore,
  getStatus,
  getTimeline,
  startWorkflow,
  manualTakeover,
} from "@/lib/api";
import type { Store, WorkflowStatus, EventLog } from "@/lib/types";
import { cn } from "@/lib/utils";
import { X, Play, RefreshCw, UserCog } from "lucide-react";

interface StoreDetailModalProps {
  storeId: number | null;
  onClose: () => void;
  onWorkflowStarted: () => void;
}

type LoadingState = "idle" | "loading" | "error";

export function StoreDetailModal({
  storeId,
  onClose,
  onWorkflowStarted,
}: StoreDetailModalProps) {
  const [store, setStore] = useState<Store | null>(null);
  const [status, setStatus] = useState<WorkflowStatus | null>(null);
  const [events, setEvents] = useState<EventLog[]>([]);
  const [loadState, setLoadState] = useState<LoadingState>("idle");
  const [actionLoading, setActionLoading] = useState(false);

  const isOpen = storeId !== null;

  useEffect(() => {
    if (!storeId) return;

    let cancelled = false;
    setLoadState("loading");
    setStore(null);
    setStatus(null);
    setEvents([]);

    async function load() {
      if (!storeId) return;
      try {
        const [s, st, ev] = await Promise.all([
          getStore(storeId),
          getStatus(storeId),
          getTimeline(storeId),
        ]);
        if (!cancelled) {
          setStore(s);
          setStatus(st);
          setEvents(ev.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));
          setLoadState("idle");
        }
      } catch {
        if (!cancelled) {
          setLoadState("error");
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [storeId]);

  async function handleStartWorkflow() {
    if (!storeId) return;
    setActionLoading(true);
    try {
      await startWorkflow(storeId);
      onWorkflowStarted();
    } catch {
      // keep modal open on error
    } finally {
      setActionLoading(false);
    }
  }

  async function handleManualTakeover() {
    if (!storeId) return;
    setActionLoading(true);
    try {
      await manualTakeover(storeId);
      // reload status
      const st = await getStatus(storeId);
      setStatus(st);
    } catch {
      // keep modal open on error
    } finally {
      setActionLoading(false);
    }
  }

  const currentState = status?.current_state || "NEW_STORE";
  const isManualReview = currentState === "MANUAL_REVIEW";
  const isNewStore = currentState === "NEW_STORE";
  const isDone = currentState === "DONE";

  return (
    <Dialog open={isOpen} onOpenChange={(open: boolean) => !open && onClose()}>
      <DialogContent className="max-w-[900px] w-[95vw] max-h-[90vh] p-0 gap-0 overflow-hidden flex flex-col bg-ivory border-border-cream rounded-very-rounded">
        {/* HEADER */}
        {loadState === "loading" ? (
          <div className="p-6 pb-4">
            <div className="flex items-center gap-4">
              <div className="size-11 rounded-generously-rounded bg-warm-sand animate-pulse shrink-0" />
              <div className="flex flex-col gap-2 flex-1">
                <div className="h-5 w-48 bg-warm-sand animate-pulse rounded" />
                <div className="h-3 w-64 bg-warm-sand animate-pulse rounded" />
              </div>
            </div>
          </div>
        ) : loadState === "error" ? (
          <div className="p-6 text-center">
            <p className="text-error-crimson text-sm mb-3">Failed to load store details</p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                // re-trigger by changing storeId
                const id = storeId;
                if (id) {
                  setLoadState("loading");
                  Promise.all([getStore(id), getStatus(id), getTimeline(id)])
                    .then(([s, st, ev]) => {
                      setStore(s);
                      setStatus(st);
                      setEvents(ev.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));
                      setLoadState("idle");
                    })
                    .catch(() => setLoadState("error"));
                }
              }}
            >
              Retry
            </Button>
          </div>
        ) : store ? (
          <>
            <DialogHeader className="p-6 pb-4 border-b border-border-cream shrink-0">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-4">
                  {/* Avatar */}
                  <div className="size-11 rounded-generously-rounded bg-terracotta flex items-center justify-center shrink-0 text-ivory font-anthropic-serif text-lg font-medium">
                    {store.name.charAt(0)}
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <DialogTitle className="font-anthropic-serif text-[18px] font-medium text-anthropic-near-black leading-tight">
                      {store.name}
                    </DialogTitle>
                    <div className="flex items-center gap-2 text-[12px] text-stone-gray font-anthropic-mono">
                      {store.city && <span>{store.city}</span>}
                      {store.city && store.category && <span>·</span>}
                      {store.category && <span>{store.category}</span>}
                      <span>·</span>
                      <span>{store.store_id}</span>
                      <span>·</span>
                      <span className="flex items-center gap-0.5">
                        {store.rating.toFixed(1)}
                        <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor" className="text-terracotta">
                          <path d="M5 0l1.29 2.61L9 3.09l-2 1.95.47 2.74L5 6.5 2.53 7.78 3 5.04 1 3.09l2.71-.48L5 0z"/>
                        </svg>
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {status && <StateBadge state={currentState} size="md" />}

                  {/* Action buttons */}
                  {!isManualReview && !isDone && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleManualTakeover}
                      disabled={actionLoading}
                      className="text-[12px] h-8 px-3 text-stone-gray hover:text-anthropic-near-black border border-border-cream"
                    >
                      <UserCog className="size-3.5 mr-1" />
                      Manual Takeover
                    </Button>
                  )}

                  {isManualReview && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleManualTakeover}
                      disabled={actionLoading}
                      className="text-[12px] h-8 px-3 text-stone-gray hover:text-anthropic-near-black border border-border-cream"
                    >
                      <UserCog className="size-3.5 mr-1" />
                      Manual Takeover
                    </Button>
                  )}
                </div>
              </div>
            </DialogHeader>

            {/* BODY: Left + Right columns */}
            <div className="flex flex-1 min-h-0 overflow-hidden">
              {/* LEFT COLUMN */}
              <div className="flex-1 min-w-0 border-r border-border-cream flex flex-col overflow-hidden">
                <div className="p-5 pb-3 flex-1 overflow-y-auto">
                  {/* Section label */}
                  <h2 className="text-[11px] font-semibold text-stone-gray uppercase tracking-wider mb-4">
                    Workflow Progress
                  </h2>

                  {/* Vertical stepper */}
                  <div className="mb-5">
                    <WorkflowStepper currentState={currentState} />
                  </div>

                  {/* Step detail card */}
                  <div className="mb-4">
                    <StepDetailCard
                      state={currentState}
                      store={store}
                      recentAgentRuns={status?.recent_agent_runs}
                    />
                  </div>

                  {/* Failure log card */}
                  {isManualReview && status && (
                    <FailureLogCard recentAgentRuns={status.recent_agent_runs} />
                  )}
                </div>
              </div>

              {/* RIGHT COLUMN */}
              <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
                <div className="p-5 pb-3 flex flex-col h-full overflow-hidden">
                  {/* Section label */}
                  <h2 className="text-[11px] font-semibold text-stone-gray uppercase tracking-wider mb-4 shrink-0">
                    Recent Activity
                  </h2>

                  {/* Timeline */}
                  <ScrollArea className="flex-1 pr-3">
                    {events.length > 0 ? (
                      <VerticalTimeline events={events} />
                    ) : (
                      <div className="flex flex-col items-center justify-center py-12 text-stone-gray/50 italic font-serif">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="mb-2 opacity-30">
                          <circle cx="12" cy="12" r="10" />
                          <path d="M12 6v6l4 2" />
                        </svg>
                        <p className="text-sm">No activity records yet</p>
                      </div>
                    )}
                  </ScrollArea>
                </div>
              </div>
            </div>

            {/* FOOTER */}
            <div className="p-4 border-t border-border-cream flex items-center justify-between shrink-0 bg-parchment/30">
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="text-[13px] h-9 px-4 text-stone-gray hover:text-anthropic-near-black border border-border-cream bg-ivory"
              >
                Close
              </Button>

              <div className="flex items-center gap-2">
                {!isDone && (
                  <Button
                    onClick={handleStartWorkflow}
                    disabled={actionLoading}
                    className={cn(
                      "text-[13px] h-9 px-5 bg-terracotta text-ivory hover:opacity-90 border-0 shadow-sm",
                      actionLoading && "opacity-70 cursor-not-allowed"
                    )}
                  >
                    {actionLoading ? (
                      <RefreshCw className="size-3.5 mr-1 animate-spin" />
                    ) : (
                      <Play className="size-3.5 mr-1 fill-current" />
                    )}
                    {isNewStore ? "Start Workflow" : "Continue Next Step"}
                  </Button>
                )}
              </div>
            </div>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
