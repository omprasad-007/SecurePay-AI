import React from "react";

export default function RealtimeStatusPanel({ realtime }) {
  const alerts = realtime?.alerts || [];

  return (
    <section className="hmi-panel">
      <h2 className="hmi-title">Realtime Fraud Spike Status</h2>
      <p className="hmi-subtitle">Hourly spike and geo-cluster breach monitoring.</p>

      <div className="hmi-kpi-grid" style={{ marginTop: "0.8rem" }}>
        <div className="hmi-kpi">
          <span className="hmi-subtitle">Alert Active</span>
          <span className="hmi-kpi-value">{realtime?.alert_active ? "Yes" : "No"}</span>
        </div>
        <div className="hmi-kpi">
          <span className="hmi-subtitle">Spike %</span>
          <span className="hmi-kpi-value">{realtime?.fraud_spike_percentage ?? 0}%</span>
        </div>
      </div>

      <div className="hmi-table-wrap" style={{ marginTop: "0.8rem" }}>
        <table className="hmi-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Severity</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            {alerts.slice(0, 6).map((alert) => (
              <tr key={alert.id}>
                <td>{alert.alert_type}</td>
                <td>{alert.severity}</td>
                <td>{alert.message}</td>
              </tr>
            ))}
            {!alerts.length && (
              <tr>
                <td colSpan={3} className="text-muted">
                  No realtime alerts.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

