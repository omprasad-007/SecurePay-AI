import React from "react";

export default function DeviceAnomalyPanel({ data }) {
  const rows = data?.devices || [];

  return (
    <section className="hmi-panel">
      <h2 className="hmi-title">Device & Behavior Heatmap</h2>
      <p className="hmi-subtitle">KMeans clusters with explainable anomaly scoring.</p>

      <div className="hmi-table-wrap" style={{ marginTop: "0.8rem" }}>
        <table className="hmi-table">
          <thead>
            <tr>
              <th>Device</th>
              <th>Type</th>
              <th>Anomaly</th>
              <th>Cluster</th>
              <th>Level</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 10).map((row) => (
              <tr key={row.device_id}>
                <td>{row.device_id}</td>
                <td>{row.device_type}</td>
                <td>{row.anomaly_score}</td>
                <td>{row.cluster_label}</td>
                <td>{row.anomaly_level}</td>
              </tr>
            ))}
            {!rows.length && (
              <tr>
                <td colSpan={5} className="text-muted">
                  No device anomaly records for selected filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

