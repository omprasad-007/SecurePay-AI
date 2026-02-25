import { getTransactions } from "../../../utils/fraudUtils";

function num(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function clamp(value, min = 0, max = 1) {
  return Math.max(min, Math.min(max, num(value, 0)));
}

function riskLevel(score) {
  if (score <= 30) return "Low";
  if (score <= 60) return "Medium";
  if (score <= 80) return "High";
  return "Critical";
}

function normalize(tx, index = 0) {
  const timestamp = new Date(tx.timestamp || Date.now() - index * 3600 * 1000);
  const riskScore = num(tx.finalScore ?? tx.overallRiskScore ?? 0);
  return {
    transaction_id: String(tx.id || `TX_${index + 1}`),
    user_id: String(tx.userId || "unknown"),
    merchant_name: String(tx.merchant || "Unknown"),
    transaction_amount: num(tx.amount, 0),
    transaction_status: String(tx.status || tx.transactionStatus || "SUCCESS"),
    risk_score: riskScore,
    risk_level: riskLevel(riskScore),
    risk_reasons: Array.isArray(tx.riskDrivers)
      ? tx.riskDrivers.map((item) => (typeof item === "string" ? item : item.factor || "behavioral deviation"))
      : ["behavioral deviation"],
    transaction_datetime: timestamp,
    city: String(tx.location?.city || "Unknown"),
  };
}

function filterRows(rows, params = {}) {
  const now = new Date();
  const startDate = params.start_date ? new Date(params.start_date) : new Date(now.getTime() - 30 * 24 * 3600 * 1000);
  const endDate = params.end_date ? new Date(params.end_date) : now;
  endDate.setHours(23, 59, 59, 999);
  const risk = String(params.risk_level || "").toLowerCase();
  const status = String(params.transaction_status || "").toLowerCase();
  const user = String(params.user_id || "").trim();
  return rows
    .filter((row) => row.transaction_datetime >= startDate && row.transaction_datetime <= endDate)
    .filter((row) => !risk || row.risk_level.toLowerCase() === risk)
    .filter((row) => !status || row.transaction_status.toLowerCase() === status)
    .filter((row) => !user || row.user_id === user);
}

function metrics(rows) {
  const total = rows.length;
  const highRisk = rows.filter((row) => row.risk_score > 60);
  const averageRisk = total ? rows.reduce((sum, row) => sum + row.risk_score, 0) / total : 0;
  const highRiskPct = total ? (highRisk.length / total) * 100 : 0;
  return { total, highRisk, averageRisk, highRiskPct };
}

function previousPeriod(startDate, endDate) {
  const diff = Math.max(1, Math.ceil((endDate.getTime() - startDate.getTime()) / (24 * 3600 * 1000)) + 1);
  const prevEnd = new Date(startDate.getTime() - 24 * 3600 * 1000);
  const prevStart = new Date(prevEnd.getTime() - (diff - 1) * 24 * 3600 * 1000);
  return { prevStart, prevEnd };
}

function pctChange(current, previous) {
  if (previous === 0) return current > 0 ? 100 : 0;
  return ((current - previous) / previous) * 100;
}

export function fallbackRiskIntelligence(params = {}) {
  const rows = filterRows(getTransactions().map(normalize), params);
  const { total, highRisk, averageRisk, highRiskPct } = metrics(rows);

  const topUsersCounter = {};
  const locationsCounter = {};
  const patternsCounter = {};

  highRisk.forEach((row) => {
    topUsersCounter[row.user_id] = (topUsersCounter[row.user_id] || 0) + 1;
    locationsCounter[row.city] = (locationsCounter[row.city] || 0) + 1;
    row.risk_reasons.forEach((reason) => {
      patternsCounter[reason] = (patternsCounter[reason] || 0) + 1;
    });
  });

  return {
    overall_risk_score: Number(averageRisk.toFixed(2)),
    risk_classification: riskLevel(averageRisk),
    high_risk_percentage: Number(highRiskPct.toFixed(2)),
    top_suspicious_users: Object.entries(topUsersCounter)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([user_id, count]) => ({ user_id, count })),
    high_risk_locations: Object.entries(locationsCounter)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([city, count]) => ({ city, count })),
    common_fraud_patterns: Object.entries(patternsCounter)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([pattern, count]) => ({ pattern, count })),
    flagged_transactions: highRisk.slice(0, 200),
  };
}

export function fallbackSummary(params = {}) {
  const now = new Date();
  const startDate = params.start_date ? new Date(params.start_date) : new Date(now.getTime() - 30 * 24 * 3600 * 1000);
  const endDate = params.end_date ? new Date(params.end_date) : now;
  const rows = filterRows(getTransactions().map(normalize), params);
  const current = metrics(rows);

  const { prevStart, prevEnd } = previousPeriod(startDate, endDate);
  const previousRows = filterRows(getTransactions().map(normalize), {
    start_date: prevStart.toISOString().slice(0, 10),
    end_date: prevEnd.toISOString().slice(0, 10),
    risk_level: params.risk_level,
    transaction_status: params.transaction_status,
    user_id: params.user_id,
  });
  const previous = metrics(previousRows);

  const volumeChange = pctChange(current.total, previous.total);
  const fraudRateCurrent = current.total ? (current.highRisk.length / current.total) * 100 : 0;
  const fraudRatePrevious = previous.total ? (previous.highRisk.length / previous.total) * 100 : 0;
  const fraudChange = pctChange(fraudRateCurrent, fraudRatePrevious);
  const trend = current.averageRisk > previous.averageRisk + 3 ? "UP" : current.averageRisk < previous.averageRisk - 3 ? "DOWN" : "STABLE";
  return {
    start_date: startDate.toISOString().slice(0, 10),
    end_date: endDate.toISOString().slice(0, 10),
    transaction_volume: current.total,
    fraud_rate: Number(fraudRateCurrent.toFixed(2)),
    overall_risk_score: Number(current.averageRisk.toFixed(2)),
    transaction_volume_change_pct: Number(volumeChange.toFixed(2)),
    fraud_rate_change_pct: Number(fraudChange.toFixed(2)),
    risk_trend_direction: trend,
    ai_summary: `This audit period shows ${Math.abs(volumeChange).toFixed(1)}% abnormal transaction ${volumeChange >= 0 ? "increase" : "decrease"} compared to previous period. Fraud rate shows ${Math.abs(fraudChange).toFixed(1)}% ${fraudChange >= 0 ? "increase" : "decrease"} trend with risk direction ${trend}.`,
  };
}

export function fallbackCompare(params = {}) {
  const now = new Date();
  const startDate = params.start_date ? new Date(params.start_date) : new Date(now.getTime() - 30 * 24 * 3600 * 1000);
  const endDate = params.end_date ? new Date(params.end_date) : now;

  const currentRows = filterRows(getTransactions().map(normalize), params);
  const current = metrics(currentRows);
  const currentFraud = current.total ? (current.highRisk.length / current.total) * 100 : 0;

  const { prevStart, prevEnd } = previousPeriod(startDate, endDate);
  const previousRows = filterRows(getTransactions().map(normalize), {
    start_date: prevStart.toISOString().slice(0, 10),
    end_date: prevEnd.toISOString().slice(0, 10),
    risk_level: params.risk_level,
    transaction_status: params.transaction_status,
    user_id: params.user_id,
  });
  const previous = metrics(previousRows);
  const previousFraud = previous.total ? (previous.highRisk.length / previous.total) * 100 : 0;

  return {
    current_period: {
      label: "Current",
      volume: current.total,
      fraud_rate: Number(currentFraud.toFixed(2)),
      overall_risk_score: Number(current.averageRisk.toFixed(2)),
    },
    previous_period: {
      label: "Previous",
      volume: previous.total,
      fraud_rate: Number(previousFraud.toFixed(2)),
      overall_risk_score: Number(previous.averageRisk.toFixed(2)),
    },
    delta: {
      volume_change_pct: Number(pctChange(current.total, previous.total).toFixed(2)),
      fraud_rate_change_pct: Number(pctChange(currentFraud, previousFraud).toFixed(2)),
      risk_score_change_pct: Number(pctChange(current.averageRisk, previous.averageRisk).toFixed(2)),
    },
    chart: {
      bar: [
        { label: "Previous", volume: previous.total },
        { label: "Current", volume: current.total },
      ],
      line: [
        {
          label: "Previous",
          fraud_rate: Number(previousFraud.toFixed(2)),
          risk_score: Number(previous.averageRisk.toFixed(2)),
        },
        {
          label: "Current",
          fraud_rate: Number(currentFraud.toFixed(2)),
          risk_score: Number(current.averageRisk.toFixed(2)),
        },
      ],
    },
  };
}

export function fallbackAlerts(params = {}) {
  const rows = filterRows(getTransactions().map(normalize), params);
  const { averageRisk, highRiskPct } = metrics(rows);
  const alert = averageRisk > 70 || highRiskPct > 25
    ? [
      {
        id: `fallback-alert-${Date.now()}`,
        title: "High Risk Audit Detected",
        message: `overall_risk=${averageRisk.toFixed(2)}, high_risk_pct=${highRiskPct.toFixed(2)}`,
        severity: "HIGH",
        trigger_payload: {
          overall_risk_score: Number(averageRisk.toFixed(2)),
          high_risk_percentage: Number(highRiskPct.toFixed(2)),
        },
        is_read: false,
        is_resolved: false,
        created_at: new Date().toISOString(),
      },
    ]
    : [];
  return { unread_count: alert.length, total: alert.length, alerts: alert };
}

export function fallbackUploadSummary(rows = []) {
  const normalized = rows.map(normalize);
  const { total, highRisk, averageRisk } = metrics(normalized);
  const distribution = { Low: 0, Medium: 0, High: 0, Critical: 0 };
  normalized.forEach((row) => {
    distribution[row.risk_level] = (distribution[row.risk_level] || 0) + 1;
  });
  return {
    success: true,
    preview: normalized.slice(0, 10),
    totalRows: total,
    summary: {
      uploaded_records: rows.length,
      stored_records: total,
      flagged_records: highRisk.length,
      average_risk_score: Number(averageRisk.toFixed(2)),
      risk_level_distribution: distribution,
    },
    message: "Local analysis complete (backend upload plugin unavailable).",
  };
}
