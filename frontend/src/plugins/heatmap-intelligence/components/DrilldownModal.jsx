import React from "react";

export default function DrilldownModal({ open, data, onClose }) {
  if (!open) return null;

  return (
    <div className="hmi-modal-backdrop" onClick={onClose}>
      <div className="hmi-modal" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
          <h3 className="hmi-title" style={{ margin: 0 }}>Heat Zone Drill-Down</h3>
          <button className="btn-outline" onClick={onClose}>Close</button>
        </div>

        <div className="hmi-kpi-grid" style={{ marginTop: "0.8rem" }}>
          <div className="hmi-kpi">
            <span className="hmi-subtitle">Total Transactions</span>
            <span className="hmi-kpi-value">{data?.total_transactions ?? 0}</span>
          </div>
          <div className="hmi-kpi">
            <span className="hmi-subtitle">Fraud %</span>
            <span className="hmi-kpi-value">{data?.fraud_percentage ?? 0}%</span>
          </div>
        </div>

        <h4 className="hmi-title" style={{ marginTop: "1rem", marginBottom: "0.4rem" }}>Top Users</h4>
        <div className="hmi-table-wrap">
          <table className="hmi-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Txns</th>
              </tr>
            </thead>
            <tbody>
              {(data?.top_users || []).map((row) => (
                <tr key={row.user_id}>
                  <td>{row.user_id}</td>
                  <td>{row.transaction_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h4 className="hmi-title" style={{ marginTop: "1rem", marginBottom: "0.4rem" }}>Top Devices</h4>
        <div className="hmi-table-wrap">
          <table className="hmi-table">
            <thead>
              <tr>
                <th>Device</th>
                <th>Type</th>
                <th>Txns</th>
              </tr>
            </thead>
            <tbody>
              {(data?.top_devices || []).map((row) => (
                <tr key={row.device_id}>
                  <td>{row.device_id}</td>
                  <td>{row.device_type}</td>
                  <td>{row.transaction_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p style={{ marginTop: "0.8rem", fontSize: "0.86rem", lineHeight: 1.45 }}>{data?.ai_summary || ""}</p>
      </div>
    </div>
  );
}

