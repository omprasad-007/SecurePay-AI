import React from "react";

export default function PredictiveZonesPanel({ data }) {
  const zones = data?.zones || [];

  return (
    <section className="hmi-panel">
      <h2 className="hmi-title">Predictive Fraud Zones</h2>
      <p className="hmi-subtitle">Historical trend and growth-velocity based risk escalation signals.</p>

      <div className="hmi-table-wrap" style={{ marginTop: "0.8rem" }}>
        <table className="hmi-table">
          <thead>
            <tr>
              <th>Region</th>
              <th>Predicted</th>
              <th>Growth</th>
              <th>Label</th>
            </tr>
          </thead>
          <tbody>
            {zones.slice(0, 10).map((zone, idx) => (
              <tr key={`${zone.city || "na"}-${zone.country || "na"}-${idx}`}>
                <td>{[zone.city, zone.state, zone.country].filter(Boolean).join(", ") || "Unknown"}</td>
                <td>{zone.predicted_risk_score}</td>
                <td>{zone.growth_rate}</td>
                <td>{zone.label}</td>
              </tr>
            ))}
            {!zones.length && (
              <tr>
                <td colSpan={4} className="text-muted">
                  No predictive zones available for selected period.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

