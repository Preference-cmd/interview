import { STATE_COLORS, STATE_LABELS } from "@/lib/types";
import { cn } from "@/lib/utils";

interface StateBadgeProps {
  state: string;
  size?: "sm" | "md";
}

export function StateBadge({ state, size = "md" }: StateBadgeProps) {
  const color = STATE_COLORS[state] || "#6b7280";
  const label = STATE_LABELS[state] || state;

  return (
    <span
      className={cn(
        "inline-block rounded-full font-semibold font-anthropic-sans",
        size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-3 py-1 text-[13px]"
      )}
      style={{
        backgroundColor: `${color}20`,
        color: color,
        border: `1px solid ${color}40`,
      }}
    >
      {label}
    </span>
  );
}
