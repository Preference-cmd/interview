"use client";

import React from "react";
import { Star, MapPin, Tag, TrendingUp, ShoppingBag, MessageSquare, AlertTriangle, Activity, MessageCircle, Users } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Store } from "@/lib/types";
import { cn } from "@/lib/utils";
import { StateBadge } from "./StateBadge";

interface StoreInfoCardProps {
  store: Store;
}

export function StoreInfoCard({ store }: StoreInfoCardProps) {
  const isRatingGood = (store.rating ?? 0) >= 3.5;
  const competitorDiscount = Math.round((1 - (store.competitor_avg_discount ?? 0)) * 100);

  const InfoRow = ({ label, value, icon: Icon }: { label: string; value: React.ReactNode; icon: any }) => (
    <div className="flex items-start gap-3">
      <div className="mt-1 bg-anthropic-near-black/[0.03] p-1.5 rounded-generously-rounded">
        <Icon className="h-4 w-4 text-olive-gray" />
      </div>
      <div>
        <p className="text-[10px] text-anthropic-near-black/40 font-mono uppercase tracking-wider">{label}</p>
        <p className="text-sm font-medium">{value}</p>
      </div>
    </div>
  );

  const MetricBox = ({ label, value, icon: Icon, iconClassName, valueClassName }: { label: string; value: React.ReactNode; icon: any, iconClassName?: string, valueClassName?: string }) => (
    <div className="space-y-1">
      <div className="flex items-center gap-1.5 mb-1">
        <Icon className={cn("h-3.5 w-3.5", iconClassName || "text-olive-gray")} />
        <p className="text-[10px] text-anthropic-near-black/40 font-mono uppercase tracking-wider">{label}</p>
      </div>
      <p className={cn("text-lg font-serif font-medium", valueClassName)}>
        {value}
      </p>
    </div>
  );

  return (
    <Card className="bg-ivory border-border-cream rounded-very-rounded shadow-whisper overflow-hidden">
      <CardHeader className="pb-4">
        <CardTitle className="font-serif text-lg flex items-center gap-2">
          Store Details
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Basic Info */}
        <div className="space-y-4">
          <InfoRow label="Location" value={store.city || "Unknown"} icon={MapPin} />
          <InfoRow label="Category" value={store.category || "Unknown"} icon={Tag} />
          <InfoRow 
            label="ROS Health" 
            value={<StateBadge state={store.ros_health} size="sm" />} 
            icon={Activity} 
          />
        </div>

        <Separator className="bg-anthropic-near-black/5" />

        {/* Performance Metrics */}
        <div className="grid grid-cols-2 gap-y-6 gap-x-4">
          <MetricBox 
            label="Rating"
            icon={Star}
            iconClassName={isRatingGood ? "text-amber-500 fill-amber-500" : "text-error-crimson fill-error-crimson"}
            valueClassName={isRatingGood ? "text-amber-600" : "text-error-crimson"}
            value={<>{(store.rating ?? 0).toFixed(1)} <span className="text-xs text-anthropic-near-black/30 font-sans">/ 5.0</span></>}
          />

          <MetricBox 
            label="7D GMV"
            icon={TrendingUp}
            value={<>¥{(store.gmv_last_7d ?? 0).toLocaleString()}</>}
          />

          <MetricBox 
            label="Orders/mo"
            icon={ShoppingBag}
            value={(store.monthly_orders ?? 0).toLocaleString()}
          />

          <MetricBox 
            label="Reviews"
            icon={MessageCircle}
            value={(store.review_count ?? 0).toLocaleString()}
          />

          <MetricBox 
            label="Reply Rate"
            icon={MessageSquare}
            value={`${((store.review_reply_rate ?? 0) * 100).toFixed(0)}%`}
          />

          <MetricBox 
            label="Comp. Discount"
            icon={Users}
            value={`-${competitorDiscount}%`}
          />
        </div>

        {/* Issues Section */}
        {store.issues && store.issues.length > 0 && (
          <>
            <Separator className="bg-anthropic-near-black/5" />
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-terracotta" />
                <p className="text-[10px] text-anthropic-near-black/40 font-mono uppercase tracking-wider">Identified Issues</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {store.issues.map((issue, idx) => (
                  <Badge 
                    key={idx}
                    className="bg-terracotta/10 text-terracotta border-terracotta/20 hover:bg-terracotta/20 font-sans font-normal text-[11px] rounded-subtly-rounded"
                  >
                    {issue}
                  </Badge>
                ))}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
