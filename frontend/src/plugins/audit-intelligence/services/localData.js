import { getTransactions, saveTransactions } from "../../../utils/fraudUtils";

function toNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function clamp(value, min = 0, max = 100) {
  return Math.max(min, Math.min(max, toNumber(value, min)));
}

export function riskLevelFromScore(score) {
  const value = clamp(score, 0, 100);
  if (value <= 30) return "Low";
  if (value <= 60) return "Medium";
  if (value <= 80) return "High";
  return "Critical";
}

function normalizeReasons(tx) {
  if (Array.isArray(tx.riskDrivers) && tx.riskDrivers.length > 0) {
    return tx.riskDrivers
      .map((item) => (typeof item === "string" ? item : item?.factor))
      .filter(Boolean);
  }
  return [];
}

export function normalizeLocalTransaction(tx, index = 0) {
  const transactionDate = new Date(tx.timestamp || Date.now() - index * 3600 * 1000);
  const score = clamp(tx.finalScore ?? tx.overallRiskScore ?? tx.risk_score ?? 0);
  const reasons = normalizeReasons(tx);
  return {
    transaction_id: String(tx.id || tx.transaction_id || `TX-${Date.now()}-${index}`),
    user_id: String(tx.userId || tx.user_id || "unknown"),
    merchant_name: String(tx.merchant || tx.merchant_name || "Unknown"),
    transaction_amount: toNumber(tx.amount ?? tx.transaction_amount, 0),
    transaction_status: String(tx.status || tx.transaction_status || "SUCCESS"),
    risk_score: score,
    risk_level: String(tx.riskLevel || tx.risk_level || riskLevelFromScore(score)),
    risk_reasons: reasons.length > 0 ? reasons : ["behavioral deviation"],
    transaction_datetime: transactionDate,
    city: String(tx.location?.city || tx.city || "Unknown"),
    device_id: String(tx.deviceId || tx.device_id || "unknown"),
    ip_address: String(tx.ip || tx.ip_address || "0.0.0.0"),
  };
}

export function readLocalAuditRows(params = {}) {
  const sourceRows = getTransactions().map(normalizeLocalTransaction);

  const endDate = params.end_date ? new Date(params.end_date) : new Date();
  const startDate = params.start_date
    ? new Date(params.start_date)
    : new Date(endDate.getTime() - 30 * 24 * 3600 * 1000);
  endDate.setHours(23, 59, 59, 999);

  const riskLevel = String(params.risk_level || "").trim().toLowerCase();
  const status = String(params.transaction_status || "").trim().toLowerCase();
  const userId = String(params.user_id || "").trim();

  return sourceRows
    .filter((row) => row.transaction_datetime >= startDate && row.transaction_datetime <= endDate)
    .filter((row) => !riskLevel || String(row.risk_level).toLowerCase() === riskLevel)
    .filter((row) => !status || String(row.transaction_status).toLowerCase() === status)
    .filter((row) => !userId || row.user_id === userId)
    .sort((a, b) => b.transaction_datetime.getTime() - a.transaction_datetime.getTime());
}

function csvEscape(value) {
  const text = String(value ?? "");
  if (text.includes(",") || text.includes('"') || text.includes("\n")) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

export function buildLocalExportArtifact(rows = [], format = "csv") {
  const fmt = String(format || "csv").toLowerCase();
  const mapped = rows.map((row) => ({
    transaction_id: row.transaction_id,
    user_id: row.user_id,
    merchant_name: row.merchant_name,
    transaction_amount: row.transaction_amount,
    transaction_status: row.transaction_status,
    risk_score: row.risk_score,
    risk_level: row.risk_level,
    risk_reasons: row.risk_reasons,
    transaction_datetime:
      row.transaction_datetime instanceof Date
        ? row.transaction_datetime.toISOString()
        : String(row.transaction_datetime || ""),
    city: row.city,
    device_id: row.device_id,
    ip_address: row.ip_address,
  }));

  if (fmt === "json") {
    return {
      blob: new Blob([JSON.stringify(mapped, null, 2)], { type: "application/json" }),
      extension: "json",
    };
  }

  const columns = [
    "transaction_id",
    "user_id",
    "merchant_name",
    "transaction_amount",
    "transaction_status",
    "risk_score",
    "risk_level",
    "risk_reasons",
    "transaction_datetime",
    "city",
    "device_id",
    "ip_address",
  ];
  const csvRows = [
    columns.join(","),
    ...mapped.map((row) =>
      columns
        .map((column) =>
          column === "risk_reasons"
            ? csvEscape(Array.isArray(row[column]) ? row[column].join(" | ") : "")
            : csvEscape(row[column])
        )
        .join(",")
    ),
  ];
  const csvText = csvRows.join("\n");

  if (fmt === "xlsx" || fmt === "excel") {
    return {
      blob: new Blob([csvText], { type: "application/vnd.ms-excel" }),
      extension: "xlsx",
    };
  }

  if (fmt === "pdf") {
    const lines = mapped
      .slice(0, 250)
      .map(
        (row) =>
          `${row.transaction_id} | ${row.merchant_name} | ${row.transaction_amount} | ${row.risk_score} | ${row.risk_level}`
      );
    const text = ["Audit Export (fallback text format)", "", ...lines].join("\n");
    return {
      blob: new Blob([text], { type: "text/plain" }),
      extension: "txt",
    };
  }

  return {
    blob: new Blob([csvText], { type: "text/csv" }),
    extension: "csv",
  };
}

function parseDate(value) {
  if (!value) return new Date();
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? new Date() : parsed;
}

function inferredReasons(source) {
  const amount = toNumber(source.transaction_amount ?? source.amount, 0);
  const timestamp = parseDate(source.transaction_datetime || source.timestamp || source.date);
  const hour = timestamp.getHours();
  const reasons = [];

  if (amount > 100000) reasons.push("abnormal amount");
  if (hour <= 5 || hour >= 23) reasons.push("unusual time");
  if (!source.device_id && !source.deviceId) reasons.push("device mismatch");
  if (!source.city && !source.location?.city) reasons.push("geo anomaly");

  return reasons.length ? reasons : ["behavioral deviation"];
}

function inferredScore(source, reasons) {
  if (source.risk_score !== undefined && source.risk_score !== null) {
    return clamp(source.risk_score);
  }
  const amount = toNumber(source.transaction_amount ?? source.amount, 0);
  const base = Math.min(55, (amount / 100000) * 40);
  const reasonBoost = reasons.length * 12;
  return clamp(base + reasonBoost + 8);
}

function localTxFromAuditRow(row, index, sourceName) {
  const timestamp = parseDate(row.transaction_datetime || row.timestamp || row.date);
  const reasons = Array.isArray(row.risk_reasons) && row.risk_reasons.length ? row.risk_reasons : inferredReasons(row);
  const score = inferredScore(row, reasons);
  const level = riskLevelFromScore(score);

  return {
    id: String(row.transaction_id || row.id || `${sourceName}-${index + 1}`),
    userId: String(row.user_id || row.userId || "UPLOAD_USER"),
    receiverId: String(row.receiver_id || row.receiverId || row.merchant_name || "UPLOAD_MERCHANT"),
    amount: toNumber(row.transaction_amount ?? row.amount, 0),
    deviceId: String(row.device_id || row.deviceId || "UPLOAD_DEVICE"),
    merchant: String(row.merchant_name || row.merchant || "Uploaded Merchant"),
    channel: String(row.channel || "UPLOAD"),
    ip: String(row.ip_address || row.ip || "0.0.0.0"),
    location: {
      city: String(row.city || "Unknown"),
      lat: toNumber(row.geo_latitude ?? row.lat, 0) || 0,
      lon: toNumber(row.geo_longitude ?? row.lon, 0) || 0,
    },
    timestamp: timestamp.toISOString(),
    finalScore: score,
    riskLevel: level,
    riskDrivers: reasons.map((reason) => ({ factor: reason, weight: 0.2 })),
    features: {
      sourceFile: sourceName,
      uploadInferred: true,
    },
  };
}

export function rowsToLocalTransactions(rows = [], sourceName = "audit-upload") {
  return rows.map((row, index) => localTxFromAuditRow(row, index, sourceName));
}

export function mergeLocalTransactions(newTransactions = []) {
  if (!newTransactions.length) return { stored: 0, total: getTransactions().length };

  const existing = getTransactions();
  const byId = new Map(existing.map((item) => [String(item.id), item]));
  newTransactions.forEach((item) => {
    byId.set(String(item.id), item);
  });
  const merged = Array.from(byId.values()).sort(
    (a, b) => new Date(b.timestamp || 0).getTime() - new Date(a.timestamp || 0).getTime()
  );

  saveTransactions(merged);
  localStorage.setItem("securepay_transactions_updated_at", new Date().toISOString());
  window.dispatchEvent(new Event("transactions-updated"));
  return { stored: newTransactions.length, total: merged.length };
}
