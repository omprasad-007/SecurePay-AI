import API_BASE_URL from "../../../config/api";
import { auth } from "../../../utils/firebase";
import { getStoredRole } from "../../../utils/themeManager";
import { localHeatmapFallback } from "./localFallback";

function toQuery(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    query.set(key, String(value));
  });
  return query.toString();
}

async function request(path, params = {}) {
  const user = auth.currentUser;
  const headers = {
    "Content-Type": "application/json",
    "X-User-Role": getStoredRole(),
  };
  if (user) {
    const token = await user.getIdToken();
    headers.Authorization = `Bearer ${token}`;
  }

  const query = toQuery(params);
  const url = `${API_BASE_URL}${path}${query ? `?${query}` : ""}`;
  let response;
  try {
    response = await fetch(url, { method: "GET", headers });
  } catch {
    return localHeatmapFallback(path, params);
  }
  if (!response.ok) {
    if (response.status === 404 || response.status >= 500) {
      return localHeatmapFallback(path, params);
    }
    const payload = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(payload.detail || "Request failed");
  }
  return response.json();
}

async function requestBlob(path, params = {}) {
  const user = auth.currentUser;
  const headers = {
    "X-User-Role": getStoredRole(),
  };
  if (user) {
    const token = await user.getIdToken();
    headers.Authorization = `Bearer ${token}`;
  }

  const query = toQuery(params);
  const url = `${API_BASE_URL}${path}${query ? `?${query}` : ""}`;
  let response;
  try {
    response = await fetch(url, { method: "GET", headers });
  } catch {
    return localHeatmapFallback(path, params, true);
  }
  if (!response.ok) {
    if (response.status === 404 || response.status >= 500) {
      return localHeatmapFallback(path, params, true);
    }
    const payload = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(payload.detail || "Request failed");
  }
  return response.blob();
}

export function getGeographicHeatmap(filters) {
  return request("/api/heatmap/geographic", filters);
}

export function getTimePattern(filters) {
  return request("/api/heatmap/time-pattern", filters);
}

export function getDeviceAnomaly(filters) {
  return request("/api/heatmap/device-anomaly", filters);
}

export function getFraudClusters(filters) {
  return request("/api/heatmap/fraud-clusters", filters);
}

export function getPredictiveRisk(filters) {
  return request("/api/heatmap/predictive-risk", filters);
}

export function getRealtimeStatus() {
  return request("/api/heatmap/realtime-status");
}

export function getSummary(filters) {
  return request("/api/heatmap/summary", filters);
}

export function getZoneDrilldown(params) {
  return request("/api/heatmap/zone-drilldown", params);
}

export function getComplianceReport(filters) {
  return request("/api/heatmap/compliance-report", filters);
}

export function getSuspiciousTransactionsReport(filters) {
  return request("/api/heatmap/suspicious-transactions-report", filters);
}

export function getSarReport(filters) {
  return request("/api/heatmap/sar", filters);
}

export function exportComplianceReport(params) {
  return requestBlob("/api/heatmap/compliance-report/export", params);
}
