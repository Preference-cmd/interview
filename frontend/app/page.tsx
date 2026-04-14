"use client";

import { useEffect, useState } from "react";
import {
  getDashboard,
  getStores,
  getAlerts,
  acknowledgeAlert,
} from "@/lib/api";
import type { DashboardSummary, Store } from "@/lib/types";
import { AlertList } from "@/components/AlertList";
import { StoreList } from "@/components/StoreList";
import {
  StatePieChart,
  ManualReviewBarChart,
  RecentRunsChart,
} from "@/components/DashboardCharts";
import { LayoutDashboard, Store as StoreIcon, Bell, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

type Tab = "dashboard" | "stores" | "alerts";

export default function DashboardPage() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [stores, setStores] = useState<Store[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  async function loadData() {
    setLoading(true);
    try {
      const [s, st, al] = await Promise.all([
        getDashboard(),
        getStores(),
        getAlerts(),
      ]);
      setSummary(s);
      setStores(st);
      setAlerts(al);
      setLastRefresh(new Date());
    } catch (e) {
      console.error("Failed to load data:", e);
    }
    setLoading(false);
  }

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, []);

  async function handleAcknowledge(alertId: number) {
    await acknowledgeAlert(alertId);
    setAlerts((prev) =>
      prev.map((a) => (a.id === alertId ? { ...a, acknowledged: true } : a))
    );
  }

  const unreadAlerts = alerts.filter((a) => !a.acknowledged).length;

  return (
    <div className="min-h-screen bg-parchment flex font-anthropic-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-ivory border-r border-border-cream flex flex-col shrink-0 sticky top-0 h-screen">
        <div className="h-16 px-6 flex items-center border-b border-border-cream">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-comfortably-rounded bg-terracotta flex items-center justify-center">
              <span className="text-ivory font-anthropic-serif font-medium text-lg leading-none">M</span>
            </div>
            <span className="font-anthropic-serif font-medium text-[20.8px] text-anthropic-near-black">
              Agent Ops
            </span>
          </div>
        </div>

        <nav className="flex-1 px-4 py-6 flex flex-col gap-2">
          {[
            { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
            { key: "stores", label: "Store List", icon: StoreIcon },
            {
              key: "alerts",
              label: `Alerts${unreadAlerts > 0 ? ` (${unreadAlerts})` : ""}`,
              icon: Bell,
            },
          ].map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setTab(key as Tab)}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-comfortably-rounded text-sm transition-colors",
                tab === key
                  ? "bg-warm-sand text-anthropic-near-black font-medium"
                  : "text-olive-gray hover:bg-parchment hover:text-anthropic-near-black"
              )}
            >
              <Icon className="w-[18px] h-[18px]" />
              {label}
            </button>
          ))}
        </nav>

        <div className="p-6 border-t border-border-cream flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-stone-gray font-anthropic-mono">
              Last updated: {lastRefresh.toLocaleTimeString("en-US")}
            </span>
            <button
              onClick={loadData}
              disabled={loading}
              className="p-1.5 rounded-subtly-rounded border border-border-cream bg-white text-olive-gray hover:bg-parchment transition-colors shadow-sm disabled:opacity-50"
            >
              <RefreshCw
                className={cn("w-3.5 h-3.5", loading && "animate-spin")}
              />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto bg-parchment">
        <div className="max-w-[1200px] mx-auto p-8 md:p-12 lg:p-16">
          <header className="mb-12">
            <h1 className="font-anthropic-serif text-[52px] font-medium text-anthropic-near-black leading-tight tracking-normal">
              {tab === "dashboard" && "Ops Dashboard"}
              {tab === "stores" && "Store Management"}
              {tab === "alerts" && "System Alerts"}
            </h1>
          </header>

          {loading && !summary && (
            <div className="py-20 text-center text-stone-gray font-anthropic-serif text-lg">
              Loading operational data...
            </div>
          )}

          {summary && (
            <div className="flex flex-col gap-12">
              {/* Dashboard Tab */}
              {tab === "dashboard" && (
                <>
                  {/* KPI Cards */}
                  <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                    <KPICard
                      label="Total Stores"
                      value={summary.total_stores.toString()}
                    />
                    <KPICard
                      label="Anomalies"
                      value={summary.anomaly_count.toString()}
                      highlight={summary.anomaly_count > 0 ? "error" : "success"}
                    />
                    <KPICard
                      label="Manual Review"
                      value={summary.manual_review_queue.length.toString()}
                      highlight="warning"
                    />
                    <KPICard
                      label="Recent Agent Runs"
                      value={summary.recent_agent_runs.length.toString()}
                    />
                  </section>

                  {/* Charts Row */}
                  <section className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    <Card title="State Distribution">
                      <StatePieChart data={summary} />
                    </Card>
                    <Card title="Review Backlog">
                      <ManualReviewBarChart data={summary} />
                    </Card>
                  </section>

                  <section className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div className="lg:col-span-2 flex flex-col gap-6">
                      <Card title="Recent Agent Activity">
                        <RecentRunsChart data={summary} />
                        <div className="mt-6">
                          <RecentRunsTable runs={summary.recent_agent_runs.slice(0, 5)} />
                        </div>
                      </Card>
                    </div>
                    <div className="flex flex-col gap-6">
                      <Card title="Latest Alerts">
                        <AlertList
                          alerts={summary.recent_alerts.slice(0, 5)}
                          onAcknowledge={handleAcknowledge}
                        />
                      </Card>
                    </div>
                  </section>
                </>
              )}

              {/* Stores Tab */}
              {tab === "stores" && (
                <div className="bg-ivory rounded-very-rounded border border-border-cream shadow-whisper p-6 overflow-hidden">
                   <StoreList stores={stores} />
                </div>
              )}

              {/* Alerts Tab */}
              {tab === "alerts" && (
                <div className="bg-ivory rounded-very-rounded border border-border-cream shadow-whisper p-6">
                   <AlertList alerts={alerts} onAcknowledge={handleAcknowledge} />
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function KPICard({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: "error" | "warning" | "success";
}) {
  return (
    <div className="bg-ivory rounded-very-rounded border border-border-cream p-6 shadow-whisper">
      <div className="text-[15px] text-olive-gray mb-3">{label}</div>
      <div
        className={cn(
          "text-[36px] font-medium font-anthropic-serif leading-tight",
          highlight === "error" && "text-error-crimson",
          highlight === "warning" && "text-terracotta",
          highlight === "success" && "text-anthropic-near-black",
          !highlight && "text-anthropic-near-black"
        )}
      >
        {value}
      </div>
    </div>
  );
}

function Card({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-ivory rounded-very-rounded border border-border-cream p-8 shadow-whisper h-full">
      <h3 className="font-anthropic-serif text-[25px] font-medium text-anthropic-near-black mb-8">
        {title}
      </h3>
      {children}
    </div>
  );
}

function RecentRunsTable({ runs }: { runs: any[] }) {
  if (runs.length === 0) {
    return <div className="text-stone-gray text-center py-8">No execution history</div>;
  }

  const AGENT_LABELS: Record<string, string> = {
    analyzer: "Diagnosis",
    web_operator: "Backend",
    mobile_operator: "Mobile",
    reporter: "Report",
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead>
          <tr className="border-b border-border-cream">
            {["Store", "Agent", "Status", "Duration"].map((h) => (
              <th
                key={h}
                className="py-3 px-2 text-stone-gray font-normal"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border-cream">
          {runs.map((run) => (
            <tr key={run.id} className="group hover:bg-parchment/50 transition-colors">
              <td className="py-3 px-2 text-anthropic-near-black max-w-[120px] truncate">
                {run.store_name}
              </td>
              <td className="py-3 px-2">
                <span className="px-2 py-1 rounded-subtly-rounded text-xs bg-warm-sand text-charcoal-warm font-medium">
                  {AGENT_LABELS[run.agent_type] || run.agent_type}
                </span>
              </td>
              <td className="py-3 px-2">
                <span
                  className={cn(
                    "font-medium",
                    run.status === "success" && "text-olive-gray",
                    run.status === "failed" && "text-error-crimson",
                    run.status === "running" && "text-terracotta"
                  )}
                >
                  {run.status === "success" ? "Success" : run.status === "failed" ? "Failed" : "Running"}
                </span>
              </td>
              <td className="py-3 px-2 text-stone-gray font-anthropic-mono text-xs">
                {run.duration_ms}ms
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
