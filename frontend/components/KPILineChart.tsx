"use client";

import React, { useState } from "react";
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

// Mock data based on Section 4.3 requirements
const mockData = [
  { day: 'Mon', gmv: 4200, orders: 120, rating: 4.2, replyRate: 85 },
  { day: 'Tue', gmv: 3800, orders: 110, rating: 4.3, replyRate: 88 },
  { day: 'Wed', gmv: 5100, orders: 145, rating: 4.1, replyRate: 82 },
  { day: 'Thu', gmv: 4800, orders: 132, rating: 4.4, replyRate: 90 },
  { day: 'Fri', gmv: 6200, orders: 168, rating: 4.5, replyRate: 92 },
  { day: 'Sat', gmv: 5500, orders: 154, rating: 4.3, replyRate: 89 },
  { day: 'Sun', gmv: 5900, orders: 162, rating: 4.4, replyRate: 91 },
];

const METRIC_CONFIG = {
  gmv: { label: "GMV", color: "#c96442", prefix: "¥", suffix: "" },
  orders: { label: "Orders", color: "#5e5d59", prefix: "", suffix: "" },
  rating: { label: "Rating", color: "#d97757", prefix: "", suffix: "" },
  replyRate: { label: "Reply Rate", color: "#4d4c48", prefix: "", suffix: "%" },
};

export function KPILineChart() {
  const [activeMetric, setActiveMetric] = useState<keyof typeof METRIC_CONFIG>("gmv");
  const config = METRIC_CONFIG[activeMetric];

  return (
    <div className="w-full flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <Tabs 
          value={activeMetric} 
          onValueChange={(v) => setActiveMetric(v as any)}
          className="w-full"
        >
          <TabsList className="bg-warm-sand/50 border-none h-8 p-1 w-fit">
            {Object.entries(METRIC_CONFIG).map(([key, { label }]) => (
              <TabsTrigger 
                key={key} 
                value={key} 
                className="text-[10px] uppercase tracking-widest font-mono h-6 px-3 data-[state=active]:bg-ivory data-[state=active]:text-anthropic-near-black data-[state=active]:shadow-sm"
              >
                {label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      <div className="h-[180px] w-full mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={mockData}>
            <defs>
              <linearGradient id="colorMetric" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={config.color} stopOpacity={0.1}/>
                <stop offset="95%" stopColor={config.color} stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid 
              strokeDasharray="3 3" 
              vertical={false} 
              stroke="#f0eee6" 
            />
            <XAxis 
              dataKey="day" 
              axisLine={false} 
              tickLine={false} 
              tick={{ fontSize: 10, fill: '#87867f', fontFamily: 'var(--font-anthropic-mono)' }} 
              dy={10}
            />
            <YAxis hide domain={['auto', 'auto']} />
            <Tooltip 
              cursor={{ stroke: '#e8e6dc', strokeWidth: 1 }}
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  return (
                    <div className="bg-ivory border border-border-cream p-2 shadow-whisper rounded-subtly-rounded outline-none">
                      <p className="text-[10px] font-mono text-stone-gray mb-1 uppercase tracking-widest">{label}</p>
                      <p className="text-sm font-serif font-medium text-anthropic-near-black">
                        {config.prefix}{payload[0].value}{config.suffix}
                      </p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Area 
              type="monotone" 
              dataKey={activeMetric} 
              stroke={config.color} 
              strokeWidth={2} 
              fillOpacity={1} 
              fill="url(#colorMetric)"
              animationDuration={1000}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
