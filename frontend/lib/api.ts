import { Store, WorkflowStatus, EventLog, DashboardSummary, Alert } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json();
}

export async function importStores(stores: any[]) {
  const res = await fetch(`${API_BASE}/stores/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stores }),
  });
  if (!res.ok) throw new Error(`Import failed: ${res.status}`);
  return res.json();
}

export async function getStores(): Promise<Store[]> {
  return fetchAPI<Store[]>("/stores");
}

export async function getStore(id: number): Promise<Store> {
  return fetchAPI<Store>(`/stores/${id}`);
}

export async function startWorkflow(storeId: number) {
  const res = await fetch(`${API_BASE}/stores/${storeId}/start`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Start workflow failed: ${res.status}`);
  return res.json();
}

export async function getStatus(storeId: number): Promise<WorkflowStatus> {
  return fetchAPI<WorkflowStatus>(`/stores/${storeId}/status`);
}

export async function getTimeline(storeId: number): Promise<EventLog[]> {
  return fetchAPI<EventLog[]>(`/stores/${storeId}/timeline`);
}

export async function manualTakeover(storeId: number) {
  const res = await fetch(`${API_BASE}/stores/${storeId}/manual-takeover`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Manual takeover failed: ${res.status}`);
  return res.json();
}

export async function getDashboard(): Promise<DashboardSummary> {
  return fetchAPI<DashboardSummary>("/dashboard/summary");
}

export async function getAlerts(): Promise<Alert[]> {
  return fetchAPI<Alert[]>("/alerts");
}

export async function acknowledgeAlert(alertId: number) {
  const res = await fetch(`${API_BASE}/alerts/${alertId}/acknowledge`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Acknowledge failed: ${res.status}`);
  return res.json();
}
