import { appendAuditLog, getOrgAuditLogs, getSessionContext } from "./localStore";

function asNumber(value, fallback = 0) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function rowsToCsv(rows) {
  const headers = ["log_id", "timestamp", "user_id", "action_type", "entity_type", "entity_id"];
  const lines = rows.map((row) =>
    headers.map((header) => `"${String(row[header] ?? "").replace(/"/g, '""')}"`).join(",")
  );
  return [headers.join(","), ...lines].join("\n");
}

export function getAuditLogs(params = {}) {
  const { organization } = getSessionContext();
  let logs = getOrgAuditLogs(organization.id);

  if (params.action_type) {
    const target = String(params.action_type).toUpperCase();
    logs = logs.filter((row) => String(row.action_type || "").toUpperCase() === target);
  }
  if (params.user_id) {
    const target = String(params.user_id);
    logs = logs.filter((row) => String(row.user_id) === target);
  }

  const page = Math.max(1, asNumber(params.page, 1));
  const pageSize = Math.max(1, asNumber(params.page_size, 50));
  const start = (page - 1) * pageSize;
  const items = logs.slice(start, start + pageSize);

  return { items, total: logs.length, page, page_size: pageSize };
}

export function exportAuditLogs(params = {}) {
  const { organization, user } = getSessionContext();
  const list = getAuditLogs({ ...params, page: 1, page_size: 100000 }).items;
  const csv = rowsToCsv(list);

  appendAuditLog({
    organizationId: organization.id,
    userId: user.id,
    actionType: "DOWNLOAD",
    entityType: "AUDIT_EXPORT",
    entityId: `audit_export_${Date.now()}`,
    details: { rows: list.length, format: "csv" },
  });

  return new Blob([csv], { type: "text/csv;charset=utf-8;" });
}
