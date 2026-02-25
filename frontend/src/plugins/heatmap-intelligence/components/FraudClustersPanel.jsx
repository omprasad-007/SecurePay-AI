import React from "react";

export default function FraudClustersPanel({ data }) {
  const clusters = data?.clusters || [];

  return (
    <section className="hmi-panel">
      <h2 className="hmi-title">AI Fraud Cluster Detection</h2>
      <p className="hmi-subtitle">Graph-based ring detection with shared device/IP/account signals.</p>
      <div className="hmi-table-wrap" style={{ marginTop: "0.8rem" }}>
        <table className="hmi-table">
          <thead>
            <tr>
              <th>Cluster</th>
              <th>Users</th>
              <th>Devices</th>
              <th>Risk Score</th>
            </tr>
          </thead>
          <tbody>
            {clusters.slice(0, 8).map((cluster) => (
              <tr key={cluster.cluster_id}>
                <td>{cluster.cluster_id}</td>
                <td>{cluster.users.length}</td>
                <td>{cluster.shared_devices.length}</td>
                <td>{cluster.ring_risk_score}</td>
              </tr>
            ))}
            {!clusters.length && (
              <tr>
                <td colSpan={4} className="text-muted">
                  No fraud clusters detected in selected range.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

