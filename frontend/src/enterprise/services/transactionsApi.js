import {
  appendAuditLog,
  applyFraudThreshold,
  getOrgComments,
  getOrgTransactions,
  getSessionContext,
  nowIso,
  saveOrgComments,
  saveOrgTransactions,
  seedOrgTransactions,
} from "./localStore";

function asNumber(value, fallback = 0) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function randomRisk(amount) {
  const base = Math.min(85, asNumber(amount, 0) / 220);
  const jitter = Math.random() * 25;
  return Math.min(99, Math.max(5, base + jitter));
}

function listByParams(transactions, params = {}) {
  let rows = [...transactions];
  const merchant = String(params.merchant || "").trim().toLowerCase();
  const riskMin = asNumber(params.risk_min, null);
  const fraudOnly = String(params.fraud_only || "").toLowerCase() === "true" || params.fraud_only === true;

  if (merchant) {
    rows = rows.filter((item) => String(item.merchant_name || "").toLowerCase().includes(merchant));
  }
  if (Number.isFinite(riskMin)) {
    rows = rows.filter((item) => asNumber(item.risk_score, 0) >= riskMin);
  }
  if (fraudOnly) {
    rows = rows.filter((item) => item.is_flagged);
  }

  rows.sort((a, b) => new Date(b.updated_at || b.created_at || 0).getTime() - new Date(a.updated_at || a.created_at || 0).getTime());
  return rows;
}

function paginate(rows, page, pageSize) {
  const safePage = Math.max(1, asNumber(page, 1));
  const safePageSize = Math.max(1, asNumber(pageSize, 20));
  const start = (safePage - 1) * safePageSize;
  return {
    items: rows.slice(start, start + safePageSize),
    total: rows.length,
    page: safePage,
    page_size: safePageSize,
  };
}

function toCsv(rows) {
  const headers = [
    "transaction_id",
    "merchant_name",
    "transaction_amount",
    "currency",
    "risk_score",
    "is_flagged",
    "transaction_status",
    "city",
    "country",
    "created_at",
  ];
  const body = rows.map((row) =>
    headers
      .map((header) => {
        const value = row[header] ?? "";
        return `"${String(value).replace(/"/g, '""')}"`;
      })
      .join(",")
  );
  return [headers.join(","), ...body].join("\n");
}

function currentState() {
  const { organization, user } = getSessionContext();
  const existing = getOrgTransactions(organization.id);
  if (!existing.length) {
    seedOrgTransactions(organization.id, user.id, organization.fraud_threshold);
  }
  return { organization, user };
}

export function createTransaction(payload = {}) {
  const { organization, user } = currentState();
  const transactions = getOrgTransactions(organization.id);

  const now = new Date();
  const riskScore = asNumber(payload.risk_score, randomRisk(payload.transaction_amount));
  const row = applyFraudThreshold(
    {
      transaction_id: `txn_${Math.random().toString(36).slice(2, 8)}_${Date.now().toString(36)}`,
      upi_id: payload.upi_id || `${user.email.split("@")[0]}@bank`,
      sender_name: payload.sender_name || user.full_name || user.email,
      receiver_name: payload.receiver_name || payload.merchant_name || "Receiver",
      merchant_name: payload.merchant_name || "Unknown Merchant",
      merchant_category: payload.merchant_category || "General",
      transaction_amount: asNumber(payload.transaction_amount, 0),
      currency: payload.currency || "INR",
      transaction_type: payload.transaction_type || "UPI",
      transaction_status: payload.transaction_status || "SUCCESS",
      transaction_date: payload.transaction_date || now.toISOString().slice(0, 10),
      transaction_time: payload.transaction_time || now.toTimeString().slice(0, 8),
      geo_latitude: payload.geo_latitude ?? null,
      geo_longitude: payload.geo_longitude ?? null,
      city: payload.city || null,
      state: payload.state || null,
      country: payload.country || null,
      ip_address: payload.ip_address || null,
      device_id: payload.device_id || null,
      device_type: payload.device_type || null,
      risk_score: riskScore,
      is_flagged: false,
      is_frozen: payload.is_frozen || false,
      notes: payload.notes || "",
      tags: Array.isArray(payload.tags) ? payload.tags : [],
      fraud_signals: Array.isArray(payload.fraud_signals) ? payload.fraud_signals : [],
      user_id: payload.user_id || user.id,
      created_by: user.id,
      organization_id: organization.id,
      created_at: nowIso(),
      updated_at: nowIso(),
    },
    organization.fraud_threshold
  );

  transactions.unshift(row);
  saveOrgTransactions(organization.id, transactions);
  appendAuditLog({
    organizationId: organization.id,
    userId: user.id,
    actionType: "CREATE",
    entityType: "TRANSACTION",
    entityId: row.transaction_id,
    details: { amount: row.transaction_amount, risk_score: row.risk_score },
  });

  return row;
}

export function getTransactions(params = {}) {
  const { organization } = currentState();
  const transactions = getOrgTransactions(organization.id);
  const filtered = listByParams(transactions, params);
  return paginate(filtered, params.page || 1, params.page_size || 20);
}

export function updateTransaction(transactionId, payload = {}) {
  const { organization, user } = currentState();
  const transactions = getOrgTransactions(organization.id);
  const index = transactions.findIndex((row) => row.transaction_id === transactionId);
  if (index < 0) throw new Error("Transaction not found");

  const merged = applyFraudThreshold(
    {
      ...transactions[index],
      ...payload,
      transaction_id: transactions[index].transaction_id,
      organization_id: transactions[index].organization_id,
      updated_at: nowIso(),
    },
    organization.fraud_threshold
  );
  transactions[index] = merged;
  saveOrgTransactions(organization.id, transactions);

  appendAuditLog({
    organizationId: organization.id,
    userId: user.id,
    actionType: "UPDATE",
    entityType: "TRANSACTION",
    entityId: transactionId,
    details: { updated_fields: Object.keys(payload || {}) },
  });

  return merged;
}

export function deleteTransaction(transactionId) {
  const { organization, user } = currentState();
  const transactions = getOrgTransactions(organization.id);
  const next = transactions.filter((row) => row.transaction_id !== transactionId);
  if (next.length === transactions.length) {
    throw new Error("Transaction not found");
  }
  saveOrgTransactions(organization.id, next);

  appendAuditLog({
    organizationId: organization.id,
    userId: user.id,
    actionType: "DELETE",
    entityType: "TRANSACTION",
    entityId: transactionId,
  });
  return { status: "deleted" };
}

export function exportTransactions(params = {}) {
  const { organization, user } = currentState();
  const rows = listByParams(getOrgTransactions(organization.id), params);
  const csv = toCsv(rows);

  appendAuditLog({
    organizationId: organization.id,
    userId: user.id,
    actionType: "DOWNLOAD",
    entityType: "TRANSACTION_EXPORT",
    entityId: `export_${Date.now()}`,
    details: { rows: rows.length, format: "csv" },
  });

  return new Blob([csv], { type: "text/csv;charset=utf-8;" });
}

export function downloadTransactionReport(transactionId) {
  const { organization, user } = currentState();
  const row = getOrgTransactions(organization.id).find((item) => item.transaction_id === transactionId);
  if (!row) throw new Error("Transaction not found");

  const report = [
    "SecurePay Enterprise Transaction Report",
    `Transaction ID: ${row.transaction_id}`,
    `Merchant: ${row.merchant_name}`,
    `Amount: ${row.currency} ${row.transaction_amount}`,
    `Risk Score: ${row.risk_score}`,
    `Risk Flagged: ${row.is_flagged ? "Yes" : "No"}`,
    `Location: ${row.city || "-"}, ${row.country || "-"}`,
    `Created At: ${row.created_at}`,
  ].join("\n");

  appendAuditLog({
    organizationId: organization.id,
    userId: user.id,
    actionType: "DOWNLOAD",
    entityType: "TRANSACTION_REPORT",
    entityId: row.transaction_id,
  });

  return new Blob([report], { type: "text/plain;charset=utf-8;" });
}

export function addTransactionComment(transactionId, comment) {
  const { organization, user } = currentState();
  const trimmed = String(comment || "").trim();
  if (!trimmed) throw new Error("Comment is required");

  const comments = getOrgComments(organization.id);
  const entry = {
    id: `cmt_${Math.random().toString(36).slice(2, 8)}_${Date.now().toString(36)}`,
    transaction_id: transactionId,
    user_id: user.id,
    comment: trimmed,
    created_at: nowIso(),
  };
  comments.unshift(entry);
  saveOrgComments(organization.id, comments);

  appendAuditLog({
    organizationId: organization.id,
    userId: user.id,
    actionType: "COMMENT",
    entityType: "TRANSACTION",
    entityId: transactionId,
  });

  return entry;
}

export function getTransactionComments(transactionId) {
  const { organization } = currentState();
  return getOrgComments(organization.id).filter((item) => item.transaction_id === transactionId);
}
