import React from "react";

function severityClass(value) {
  const normalized = String(value || "").toUpperCase();
  if (normalized === "HIGH" || normalized === "CRITICAL") return "badge badge-high";
  if (normalized === "MEDIUM") return "badge badge-medium";
  return "badge badge-low";
}

export default function AuditAlertsPanel({ alerts, loading }) {
  if (loading) {
    return (
      <section className="card ai-plugin-card">
        <p className="ai-plugin-subtle">Loading alert feed...</p>
      </section>
    );
  }

  const records = Array.isArray(alerts?.alerts) ? alerts.alerts : [];
  const unread = Number(alerts?.unread_count || 0);

  return (
    <section className="card ai-plugin-card space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Auto High-Risk Alerts</h3>
        <span className="badge badge-high">{unread} unread</span>
      </div>

      {!records.length && <p className="ai-plugin-subtle">No active alerts for the selected period.</p>}

      {records.slice(0, 8).map((alert) => (
        <article key={alert.id} className="ai-alert">
          <div className="flex items-center justify-between gap-2">
            <p className="font-medium">{alert.title}</p>
            <span className={severityClass(alert.severity)}>{alert.severity || "INFO"}</span>
          </div>
          <p className="text-sm mt-2">{alert.message}</p>
          <p className="ai-plugin-subtle mt-2">
            {alert.created_at ? new Date(alert.created_at).toLocaleString() : "Unknown time"}
          </p>
        </article>
      ))}
    </section>
  );
}
