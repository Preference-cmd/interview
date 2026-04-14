"use client";

import { Store } from "@/lib/types";
import { StateBadge } from "@/components/StateBadge";
import { getStatus } from "@/lib/api";
import { useEffect, useState } from "react";
import { Star } from "lucide-react";
import { cn } from "@/lib/utils";

interface StoreListProps {
  stores: Store[];
  onSelectStore: (storeId: number) => void;
}

export function StoreList({ stores, onSelectStore }: StoreListProps) {
  const [storeStatuses, setStoreStatuses] = useState<Record<number, any>>({});

  useEffect(() => {
    stores.forEach((store) => {
      getStatus(store.id)
        .then((status) => {
          setStoreStatuses((prev) => ({ ...prev, [store.id]: status }));
        })
        .catch(() => {
          // Store has no workflow yet — skip silently
        });
    });
  }, [stores]);

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-sm">
        <thead>
          <tr className="border-b-2 border-border-cream bg-parchment/30">
            {["Store Name", "City", "Category", "Rating", "ROS Health", "Status", "Recent Failures", "Actions"].map(
              (h) => (
                <th
                  key={h}
                  className="py-4 px-4 text-stone-gray font-medium whitespace-nowrap"
                >
                  {h}
                </th>
              )
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-border-cream">
          {stores.map((store) => {
            const status = storeStatuses[store.id];
            return (
              <tr
                key={store.id}
                className="cursor-pointer hover:bg-parchment/50 transition-colors"
                onClick={() => onSelectStore(store.id)}
              >
                <td className="py-4 px-4">
                  <div className="font-medium text-anthropic-near-black">{store.name}</div>
                  <div className="text-[11px] text-stone-gray font-anthropic-mono">
                    {store.store_id}
                  </div>
                </td>
                <td className="py-4 px-4 text-olive-gray">{store.city}</td>
                <td className="py-4 px-4 text-olive-gray">{store.category}</td>
                <td className="py-4 px-4">
                  <div className="flex items-center gap-1">
                    <span className={cn(
                      "font-semibold",
                      store.rating < 3.5 ? "text-error-crimson" : "text-anthropic-near-black"
                    )}>
                      {store.rating.toFixed(1)}
                    </span>
                    <Star className="size-3 fill-current text-terracotta" />
                  </div>
                </td>
                <td className="py-4 px-4">
                  <span
                    className={cn(
                      "px-2 py-0.5 rounded-full text-[11px] font-medium",
                      store.ros_health === "high"
                        ? "bg-green-100 text-green-700"
                        : store.ros_health === "medium"
                        ? "bg-amber-100 text-amber-700"
                        : "bg-red-100 text-red-700"
                    )}
                  >
                    {store.ros_health === "high" ? "Healthy" : store.ros_health === "medium" ? "Warning" : "Critical"}
                  </span>
                </td>
                <td className="py-4 px-4">
                  {status ? (
                    <StateBadge state={status.current_state} size="sm" />
                  ) : (
                    <span className="text-stone-gray opacity-40">—</span>
                  )}
                </td>
                <td className="py-4 px-4 text-center">
                  {status && status.consecutive_failures > 0 ? (
                    <span className="text-error-crimson font-anthropic-mono text-xs font-medium">
                      {status.consecutive_failures} times
                    </span>
                  ) : (
                    <span className="text-stone-gray opacity-40">—</span>
                  )}
                </td>
                <td className="py-4 px-4">
                  <span className="text-[11px] text-stone-gray/50">Click to view</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
