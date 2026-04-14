"use client";

import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { STATE_COLORS, STATE_LABELS, DashboardSummary } from "@/lib/types";

interface DashboardChartsProps {
  data: DashboardSummary;
}

// Warm design tokens for charts
const THEME_COLORS = {
  terracotta: "#c96442",
  olive: "#5e5d59",
  charcoal: "#4d4c48",
  sand: "#e8e6dc",
  silver: "#b0aea5",
  crimson: "#b53333",
  blue: "#3898ec",
};

export function StatePieChart({ data }: DashboardChartsProps) {
  const chartData = Object.entries(data.state_distribution)
    .filter(([_, count]) => count > 0)
    .map(([state, count]) => ({
      name: STATE_LABELS[state] || state,
      value: count,
      state,
    }));

  if (chartData.length === 0) {
    return <div className="text-stone-gray text-center py-12 italic">No distribution data available</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={100}
          paddingAngle={4}
          dataKey="value"
          stroke="none"
        >
          {chartData.map((entry) => (
            <Cell
              key={entry.state}
              fill={STATE_COLORS[entry.state] || THEME_COLORS.olive}
              className="hover:opacity-80 transition-opacity"
            />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: any, name: any) => [`${value} Stores`, name]}
          contentStyle={{
            backgroundColor: "#faf9f5",
            borderRadius: "12px",
            border: "1px solid #f0eee6",
            fontSize: "12px",
            boxShadow: "0 4px 24px rgba(0,0,0,0.05)",
            fontFamily: "Anthropic Sans, Arial",
          }}
        />
        <Legend 
          verticalAlign="bottom" 
          height={36} 
          iconType="circle"
          iconSize={8}
          wrapperStyle={{
            fontSize: '11px',
            fontFamily: 'Anthropic Sans',
            paddingTop: '20px'
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function ManualReviewBarChart({ data }: DashboardChartsProps) {
  const queue = data.manual_review_queue;
  if (queue.length === 0) {
    return <div className="text-stone-gray text-center py-16 italic">No review backlog</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart
        data={[{ name: "Manual Review", count: queue.length }]}
        layout="vertical"
        margin={{ left: 0, right: 40, top: 20, bottom: 20 }}
      >
        <XAxis type="number" hide />
        <YAxis type="category" dataKey="name" tick={{ fontSize: 12, fill: '#5e5d59' }} width={80} />
        <Tooltip
          formatter={(value: any) => [`${value} Stores`, "Pending"]}
          contentStyle={{
            backgroundColor: "#faf9f5",
            borderRadius: "12px",
            border: "1px solid #f0eee6",
            fontSize: "12px",
            fontFamily: "Anthropic Sans",
          }}
        />
        <Bar dataKey="count" fill={THEME_COLORS.crimson} radius={[0, 8, 8, 0]} barSize={40} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function RecentRunsChart({ data }: DashboardChartsProps) {
  const runs = data.recent_agent_runs.slice(0, 10).reverse();
  if (runs.length === 0) {
    return <div className="text-stone-gray text-center py-16 italic">No execution history</div>;
  }

  const agentCounts: Record<string, number> = {};
  for (const run of runs) {
    agentCounts[run.agent_type] = (agentCounts[run.agent_type] || 0) + 1;
  }
  const chartData = Object.entries(agentCounts).map(([type, count]) => ({
    name: type,
    count,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={chartData} margin={{ left: -20, right: 20, top: 20, bottom: 0 }}>
        <XAxis 
          dataKey="name" 
          tick={{ fontSize: 11, fill: '#87867f' }} 
          axisLine={{ stroke: '#f0eee6' }}
          tickLine={false}
        />
        <YAxis 
          tick={{ fontSize: 11, fill: '#87867f' }} 
          width={60} 
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          formatter={(value: any) => [`${value} Runs`, "Executions"]}
          cursor={{ fill: '#f5f4ed' }}
          contentStyle={{
            backgroundColor: "#faf9f5",
            borderRadius: "12px",
            border: "1px solid #f0eee6",
            fontSize: "12px",
            fontFamily: "Anthropic Sans",
          }}
        />
        <Bar dataKey="count" fill={THEME_COLORS.terracotta} radius={[6, 6, 0, 0]} barSize={32} />
      </BarChart>
    </ResponsiveContainer>
  );
}
