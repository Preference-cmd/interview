import { Alert } from "@/lib/types";
import { acknowledgeAlert } from "@/lib/api";
import { AlertTriangle, AlertCircle, Info, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface AlertListProps {
  alerts: Alert[];
  onAcknowledge?: (id: number) => void;
}

function AlertIcon({ severity }: { severity: string }) {
  if (severity === "critical") return <AlertTriangle className="w-4 h-4 text-error-crimson" />;
  if (severity === "warning") return <AlertCircle className="w-4 h-4 text-terracotta" />;
  return <Info className="w-4 h-4 text-olive-gray" />;
}

function formatTime(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return d.toLocaleDateString("en-US");
}

export function AlertList({ alerts, onAcknowledge }: AlertListProps) {
  if (alerts.length === 0) {
    return (
      <div className="p-8 text-center text-stone-gray flex flex-col items-center">
        <CheckCircle className="w-8 h-8 mb-2 opacity-40" />
        <p>No alerts found</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className={cn(
            "flex items-start gap-3 p-4 rounded-comfortably-rounded border transition-all",
            alert.acknowledged
              ? "bg-parchment/50 border-transparent opacity-60 grayscale"
              : "bg-ivory border-border-cream shadow-sm"
          )}
        >
          <div className="mt-0.5 shrink-0">
            <AlertIcon severity={alert.severity} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="font-medium text-[13px] text-anthropic-near-black truncate">
                {alert.store_name}
              </span>
              <span
                className={cn(
                  "text-[11px] px-1.5 py-0.5 rounded-sharp whitespace-nowrap",
                  alert.severity === "critical"
                    ? "bg-error-crimson/10 text-error-crimson"
                    : alert.severity === "warning"
                    ? "bg-terracotta/10 text-terracotta"
                    : "bg-olive-gray/10 text-olive-gray"
                )}
              >
                {alert.alert_type}
              </span>
            </div>
            <p className="text-[13px] text-olive-gray m-0 line-clamp-2 leading-snug">
              {alert.message}
            </p>
            <p className="text-[11px] text-stone-gray m-0 mt-1 font-anthropic-mono">
              {formatTime(alert.created_at)}
            </p>
          </div>
          {!alert.acknowledged && onAcknowledge && (
            <button
              onClick={() => onAcknowledge(alert.id)}
              className="shrink-0 px-2.5 py-1 rounded-subtly-rounded border border-border-cream bg-white text-xs text-charcoal-warm hover:bg-warm-sand transition-colors shadow-sm"
            >
              Acknowledge
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
