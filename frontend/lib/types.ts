export interface Store {
  id: number;
  store_id: string;
  name: string;
  city: string | null;
  category: string | null;
  rating: number;
  monthly_orders: number;
  gmv_last_7d: number;
  review_count: number;
  review_reply_rate: number;
  ros_health: string;
  competitor_avg_discount: number;
  issues: string[];
  created_at: string;
  updated_at: string;
}

export interface WorkflowStatus {
  store_id: number;
  store_name: string;
  current_state: string;
  consecutive_failures: number;
  retry_count: number;
  started_at: string | null;
  recent_agent_runs: AgentRun[];
}

export interface AgentRun {
  id: number;
  agent_type: string;
  status: string;
  state_at_run: string | null;
  output_data: Record<string, any>;
  error_msg: string | null;
  retry_count: number;
  duration_ms: number;
  created_at: string;
}

export interface EventLog {
  id: number;
  event_type: string;
  from_state: string | null;
  to_state: string | null;
  agent_type: string | null;
  message: string | null;
  extra_data: Record<string, any>;
  created_at: string;
}

export interface DashboardSummary {
  total_stores: number;
  state_distribution: Record<string, number>;
  anomaly_count: number;
  manual_review_queue: { store_id: number; store_name: string; state: string }[];
  recent_alerts: Alert[];
  recent_agent_runs: any[];
}

export interface Alert {
  id: number;
  store_id: number;
  store_name: string;
  alert_type: string;
  severity: string;
  message: string | null;
  acknowledged: boolean;
  created_at: string;
}

export const STATE_COLORS: Record<string, string> = {
  NEW_STORE: "#6b7280",
  DIAGNOSIS: "#3b82f6",
  FOUNDATION: "#8b5cf6",
  DAILY_OPS: "#f59e0b",
  WEEKLY_REPORT: "#10b981",
  DONE: "#22c55e",
  MANUAL_REVIEW: "#ef4444",
};

export const AGENT_LABELS: Record<string, string> = {
  analyzer: "Analyzer Agent",
  web_operator: "Web Operator Agent",
  mobile_operator: "Mobile Operator Agent",
  reporter: "Reporter Agent",
};

export const AGENT_COLORS: Record<string, string> = {
  analyzer: "#3b82f6",
  web_operator: "#8b5cf6",
  mobile_operator: "#f59e0b",
  reporter: "#10b981",
};

export const STATE_LABELS: Record<string, string> = {
  NEW_STORE: "New Store",
  DIAGNOSIS: "Diagnosing",
  FOUNDATION: "Infrastructure",
  DAILY_OPS: "Daily Ops",
  WEEKLY_REPORT: "Weekly Report",
  DONE: "Completed",
  MANUAL_REVIEW: "Manual Review",
};
