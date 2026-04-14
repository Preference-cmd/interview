"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, Play, ShieldAlert, MoreVertical, LayoutGrid, Activity, History, Star } from "lucide-react";
import { getStore, getStatus, getTimeline, manualTakeover, startWorkflow } from "@/lib/api";
import { Store, WorkflowStatus, EventLog } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { StoreInfoCard } from "@/components/StoreInfoCard";
import { StateBadge } from "@/components/StateBadge";
import { WorkflowStatusBar } from "@/components/WorkflowStatusBar";
import { VerticalTimeline } from "@/components/VerticalTimeline";
import { AgentRunsTable } from "@/components/AgentRunsTable";
import { KPILineChart } from "@/components/KPILineChart";
import { StoreDetailSkeleton } from "@/components/StoreDetailSkeleton";

export default function StoreDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const storeId = Number(id);

  const [loading, setLoading] = useState(true);
  const [store, setStore] = useState<Store | null>(null);
  const [status, setStatus] = useState<WorkflowStatus | null>(null);
  const [timeline, setTimeline] = useState<EventLog[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const [storeData, statusData, timelineData] = await Promise.all([
          getStore(storeId),
          getStatus(storeId),
          getTimeline(storeId),
        ]);
        setStore(storeData);
        setStatus(statusData);
        setTimeline(timelineData);
      } catch (err) {
        console.error("Failed to fetch store details:", err);
        setError("Failed to load store details. Please try again.");
      } finally {
        setLoading(false);
      }
    }

    if (storeId) {
      fetchData();
    }
  }, [storeId]);

  const handleManualTakeover = async () => {
    try {
      await manualTakeover(storeId);
      // Refresh status
      const statusData = await getStatus(storeId);
      setStatus(statusData);
    } catch (err) {
      console.error("Manual takeover failed:", err);
    }
  };

  const handleStartWorkflow = async () => {
    try {
      await startWorkflow(storeId);
      // Refresh status
      const statusData = await getStatus(storeId);
      setStatus(statusData);
    } catch (err) {
      console.error("Start workflow failed:", err);
    }
  };

  if (loading) {
    return <StoreDetailSkeleton />;
  }

  if (error || !store) {
    return (
      <div className="min-h-screen bg-parchment flex items-center justify-center p-8">
        <Card className="max-w-md w-full rounded-very-rounded">
          <CardHeader>
            <CardTitle className="text-error-crimson font-serif">Error</CardTitle>
            <CardDescription>{error || "Store not found"}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => router.push("/")} variant="outline" className="w-full rounded-generously-rounded">
              <ChevronLeft className="mr-2 h-4 w-4" aria-hidden="true" />
              Back to Store List
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-parchment text-anthropic-near-black selection:bg-warm-sand">
      {/* Header */}
      <header className="border-b border-anthropic-near-black/5 bg-parchment/80 backdrop-blur-md sticky top-0 z-10">
        <div className="max-w-[1200px] mx-auto px-8 min-h-16 py-4 flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-6">
            <Link 
              href="/stores" 
              className="flex items-center text-olive-gray hover:text-anthropic-near-black transition-colors gap-2 -ml-1"
            >
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
              <span className="text-sm font-medium">Back to Store List</span>
            </Link>
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-4">
                <h1 className="font-serif text-2xl md:text-4xl font-medium tracking-tight">
                  {store.name}
                </h1>
                <StateBadge state={status?.current_state || "NEW_STORE"} size="sm" />
              </div>
              <div className="flex items-center gap-3 text-xs text-anthropic-near-black/40 font-mono uppercase tracking-widest">
                <span>ID: {store.store_id}</span>
                <span className="text-anthropic-near-black/10">•</span>
                <span>{store.city}</span>
                <span className="text-anthropic-near-black/10">•</span>
                <span>{store.category}</span>
                <span className="text-anthropic-near-black/10">•</span>
                <span className="flex items-center gap-1">
                  <Star className={cn("h-3 w-3", store.rating >= 3.5 ? "text-amber-500 fill-amber-500" : "text-error-crimson fill-error-crimson")} />
                  {store.rating.toFixed(1)}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button 
              size="sm" 
              className="bg-error-crimson text-parchment hover:bg-error-crimson/90 font-medium rounded-generously-rounded"
              onClick={handleManualTakeover}
            >
              <ShieldAlert className="mr-2 h-4 w-4" aria-hidden="true" />
              Manual Takeover
            </Button>
            <Button 
              size="sm" 
              className="bg-anthropic-near-black text-white hover:bg-anthropic-near-black/90 font-medium px-6 rounded-generously-rounded"
              onClick={handleStartWorkflow}
            >
              <Play className="mr-2 h-4 w-4 fill-current" aria-hidden="true" />
              Run Agent
            </Button>
            <Separator orientation="vertical" className="h-8 mx-2 bg-anthropic-near-black/5" />
            <Button variant="ghost" size="icon" className="hover:bg-anthropic-near-black/5 rounded-generously-rounded" aria-label="More options">
              <MoreVertical className="h-5 w-5" aria-hidden="true" />
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-[1200px] mx-auto p-8">
        <div className="flex flex-col lg:flex-row gap-8 items-start">
          
          {/* Left Panel - 320px Sidebar */}
          <aside className="w-full lg:w-[320px] space-y-6 lg:sticky lg:top-24">
            <StoreInfoCard store={store} />
            
            {/* KPI Chart (Section 4.3) */}
            <Card className="bg-ivory border-border-cream rounded-very-rounded shadow-whisper overflow-hidden">
              <CardHeader className="pb-2">
                <CardTitle className="font-serif text-lg">KPI Trends</CardTitle>
                <CardDescription className="text-[10px] font-mono uppercase">Mock 7-day data</CardDescription>
              </CardHeader>
              <CardContent className="h-[240px] border-t border-anthropic-near-black/5 bg-anthropic-near-black/[0.01] pt-4">
                <KPILineChart />
              </CardContent>
            </Card>
          </aside>

          {/* Right Panel - Flexible Main Content */}
          <section className="flex-1 w-full min-w-0">
            <WorkflowStatusBar currentState={status?.current_state || "NEW_STORE"} />
            
            <Tabs defaultValue="overview" className="w-full">
              <TabsList className="bg-transparent border-b border-anthropic-near-black/5 rounded-none h-12 w-full justify-start gap-8 px-0">
                <TabsTrigger 
                  value="overview" 
                  className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-anthropic-near-black rounded-none h-12 px-2 flex gap-2"
                >
                  <LayoutGrid className="h-4 w-4" />
                  Overview
                </TabsTrigger>
                <TabsTrigger 
                  value="activity" 
                  className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-anthropic-near-black rounded-none h-12 px-2 flex gap-2"
                >
                  <Activity className="h-4 w-4" />
                  Live Activity
                </TabsTrigger>
                <TabsTrigger 
                  value="history" 
                  className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-anthropic-near-black rounded-none h-12 px-2 flex gap-2"
                >
                  <History className="h-4 w-4" />
                  History
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="overview" className="pt-6 space-y-8">
                {/* Dashboard / Metrics Placeholder (Task 2) */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <Card className="min-h-[300px] flex items-center justify-center border-dashed border-anthropic-near-black/10 bg-anthropic-near-black/[0.02] rounded-very-rounded">
                    <p className="text-sm text-anthropic-near-black/40 font-serif">Diagnostic Metrics Placeholder</p>
                  </Card>
                  <Card className="min-h-[300px] flex items-center justify-center border-dashed border-anthropic-near-black/10 bg-anthropic-near-black/[0.02] rounded-very-rounded">
                    <p className="text-sm text-anthropic-near-black/40 font-serif">Competitive Analysis Placeholder</p>
                  </Card>
                </div>

                {/* Agent Execution History Section (Task 5) */}
                <Card className="border-anthropic-near-black/5 shadow-whisper bg-ivory rounded-very-rounded overflow-hidden">
                  <CardHeader className="bg-ivory/50">
                    <div className="flex items-center gap-2">
                      <div className="size-2 rounded-full bg-terracotta animate-pulse" />
                      <CardTitle className="font-serif">Agent Execution History</CardTitle>
                    </div>
                    <CardDescription>Direct visibility into agent outputs and error logs</CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <AgentRunsTable runs={status?.recent_agent_runs || []} />
                  </CardContent>
                </Card>

                {/* Timeline Section */}
                <Card className="border-anthropic-near-black/5 shadow-whisper bg-ivory rounded-very-rounded">
                  <CardHeader>
                    <CardTitle className="font-serif">Store Timeline</CardTitle>
                    <CardDescription>Recent events and agent actions</CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <ScrollArea className="h-[500px] pr-4">
                      <VerticalTimeline events={timeline} />
                    </ScrollArea>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="activity" className="pt-6">
                <Card className="border-anthropic-near-black/5 shadow-whisper bg-ivory rounded-very-rounded overflow-hidden">
                  <CardHeader className="bg-ivory/50">
                    <CardTitle className="font-serif">Live Agent Activity Log</CardTitle>
                    <CardDescription>Detailed technical logs from recent agent executions</CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0 min-h-[500px]">
                    <AgentRunsTable runs={status?.recent_agent_runs || []} />
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="history" className="pt-6">
                <Card className="border-anthropic-near-black/5 shadow-whisper bg-ivory rounded-very-rounded">
                  <CardHeader>
                    <CardTitle className="font-serif">Full Event History</CardTitle>
                    <CardDescription>Comprehensive audit log of all store events</CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <ScrollArea className="h-[700px] pr-4">
                      <VerticalTimeline events={timeline} />
                    </ScrollArea>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </section>
        </div>
      </main>
    </div>
  );
}
