import API_BASE_URL from "../../../config/api";
import { auth } from "../../../utils/firebase";
import { getStoredRole } from "../../../utils/themeManager";
import {
  fallbackAlerts,
  fallbackCompare,
  fallbackRiskIntelligence,
  fallbackSummary,
  fallbackUploadSummary,
} from "./localFallback";
import {
  buildLocalExportArtifact,
  mergeLocalTransactions,
  readLocalAuditRows,
  rowsToLocalTransactions,
} from "./localData";

const FALLBACK_STATUSES = new Set([404, 500, 502, 503, 504]);

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function defaultDateRange(days = 30) {
  const end = new Date();
  const start = new Date(end.getTime() - days * 24 * 3600 * 1000);
  return {
    start_date: start.toISOString().slice(0, 10),
    end_date: end.toISOString().slice(0, 10),
  };
}

function withDefaultDates(params = {}) {
  const defaults = defaultDateRange(30);
  return {
    ...defaults,
    ...params,
    start_date: params.start_date || defaults.start_date,
    end_date: params.end_date || defaults.end_date,
  };
}

function toQuery(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    query.set(key, String(value));
  });
  return query.toString();
}

async function authHeaders(includeJson = true) {
  const headers = {
    "X-User-Role": getStoredRole(),
  };
  if (includeJson) {
    headers["Content-Type"] = "application/json";
  }

  const user = auth.currentUser;
  if (user) {
    const token = await user.getIdToken();
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

async function requestJson(path, { method = "GET", params = {}, body, fallback } = {}) {
  const query = toQuery(params);
  const url = `${API_BASE_URL}${path}${query ? `?${query}` : ""}`;
  const headers = await authHeaders(true);
  let response;

  try {
    response = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    if (fallback) return fallback(error);
    throw error;
  }

  if (!response.ok) {
    if (fallback && FALLBACK_STATUSES.has(response.status)) return fallback(new Error(`fallback-${response.status}`));
    const payload = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(payload.detail || "Request failed");
  }

  return response.json();
}

async function requestBlob(path, { params = {}, fallback } = {}) {
  const query = toQuery(params);
  const url = `${API_BASE_URL}${path}${query ? `?${query}` : ""}`;
  const headers = await authHeaders(false);
  let response;

  try {
    response = await fetch(url, { method: "GET", headers });
  } catch (error) {
    if (fallback) return fallback(error);
    throw error;
  }

  if (!response.ok) {
    if (fallback && FALLBACK_STATUSES.has(response.status)) return fallback(new Error(`fallback-${response.status}`));
    const payload = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(payload.detail || "Request failed");
  }

  const contentDisposition = response.headers.get("content-disposition") || "";
  const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/i);
  const fileName = filenameMatch?.[1] || "";
  const blob = await response.blob();
  return {
    blob,
    filename: fileName,
  };
}

async function fallbackUpload(normalizedRows = [], fileName = "audit-upload") {
  if (!normalizedRows.length) {
    throw new Error("Backend audit upload endpoint unavailable and local fallback requires CSV/JSON preview rows.");
  }

  const localTransactions = rowsToLocalTransactions(normalizedRows, fileName);
  mergeLocalTransactions(localTransactions);
  return fallbackUploadSummary(localTransactions);
}

export async function getRiskIntelligence(params = {}) {
  const query = withDefaultDates(params);
  return requestJson("/api/risk/intelligence", {
    params: query,
    fallback: () => fallbackRiskIntelligence(query),
  });
}

export async function getAuditSummary(params = {}) {
  const query = withDefaultDates(params);
  return requestJson("/api/audit/summary", {
    params: query,
    fallback: () => fallbackSummary(query),
  });
}

export async function getAuditCompare(params = {}) {
  const query = withDefaultDates(params);
  return requestJson("/api/audit/compare", {
    params: query,
    fallback: () => fallbackCompare(query),
  });
}

export async function getAuditAlerts(params = {}) {
  return requestJson("/api/alerts", {
    params: { limit: params.limit || 50 },
    fallback: () => fallbackAlerts(withDefaultDates(params)),
  });
}

export async function sendAuditEmailReport(payload) {
  const body = {
    start_date: payload.start_date || todayIso(),
    end_date: payload.end_date || todayIso(),
    email: String(payload.email || "").trim(),
  };
  if (!body.email) throw new Error("Email is required.");

  return requestJson("/api/audit/email-report", {
    method: "POST",
    body,
    fallback: () => ({
      status: "LOCAL_SIMULATED",
      report_id: `local-report-${Date.now()}`,
      email: body.email,
    }),
  });
}

export async function downloadAuditExport(params = {}) {
  const query = withDefaultDates(params);
  const format = String(query.format || "csv").toLowerCase();

  const result = await requestBlob("/api/audit/export", {
    params: query,
    fallback: () => {
      const rows = readLocalAuditRows(query);
      const artifact = buildLocalExportArtifact(rows, format);
      return {
        blob: artifact.blob,
        filename: `audit_export_${query.start_date}_${query.end_date}.${artifact.extension}`,
      };
    },
  });

  const defaultName = `audit_export_${query.start_date}_${query.end_date}.${format === "excel" ? "xlsx" : format}`;
  return {
    blob: result.blob,
    filename: result.filename || defaultName,
  };
}

export async function uploadAuditTransactions(file, normalizedRows = []) {
  if (!file) throw new Error("Upload file is required.");

  const headers = await authHeaders(false);
  const formData = new FormData();
  formData.append("file", file);
  const url = `${API_BASE_URL}/api/audit/upload`;

  let response;
  try {
    response = await fetch(url, { method: "POST", headers, body: formData });
  } catch {
    return fallbackUpload(normalizedRows, file.name);
  }

  if (!response.ok) {
    if (FALLBACK_STATUSES.has(response.status)) {
      return fallbackUpload(normalizedRows, file.name);
    }
    const payload = await response.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(payload.detail || "Upload failed");
  }

  return response.json();
}

export function saveBlobAsFile(blob, fileName) {
  const safeName = String(fileName || `audit_export_${Date.now()}.csv`);
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = safeName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}
