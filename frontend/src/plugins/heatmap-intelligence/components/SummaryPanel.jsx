import React, { useMemo, useState } from "react";
import { Bar, ComposedChart, CartesianGrid, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function SummaryPanel({ summary, compliance }) {
  const timeline = summary?.timeline || [];
  const layers = summary?.layers || {};
  const timelineLayer = useMemo(() => layers.risk_evolution_timeline || timeline, [layers.risk_evolution_timeline, timeline]);
  const [timelineIndex, setTimelineIndex] = useState(0);
  const selectedPoint = timelineLayer[Math.max(0, Math.min(timelineIndex, timelineLayer.length - 1))];

  return (
    <section className="hmi-panel">
      <h2 className="hmi-title">AI Summary Panel</h2>
      <p className="hmi-subtitle">Comparative trend, intelligence layers, and compliance posture.</p>

      <div className="hmi-kpi-grid" style={{ marginTop: "0.8rem" }}>
        <div className="hmi-kpi">
          <span className="hmi-subtitle">Overall Risk</span>
          <span className="hmi-kpi-value">{summary?.overall_risk_score ?? 0}</span>
        </div>
        <div className="hmi-kpi">
          <span className="hmi-subtitle">Fraud Concentration Change</span>
          <span className="hmi-kpi-value">{summary?.fraud_concentration_change_pct ?? 0}%</span>
        </div>
        <div className="hmi-kpi">
          <span className="hmi-subtitle">Top Region</span>
          <span className="hmi-kpi-value" style={{ fontSize: "0.9rem" }}>{summary?.top_region || "N/A"}</span>
        </div>
        <div className="hmi-kpi">
          <span className="hmi-subtitle">Peak Time Window</span>
          <span className="hmi-kpi-value" style={{ fontSize: "0.9rem" }}>{summary?.top_time_window || "N/A"}</span>
        </div>
      </div>

      <p style={{ marginTop: "0.8rem", fontSize: "0.88rem", lineHeight: 1.5 }}>{summary?.ai_summary || "No summary available."}</p>

      <div style={{ height: 220, marginTop: "0.6rem" }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={timeline}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.25)" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} />
            <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            <Bar yAxisId="left" dataKey="transaction_volume" name="Volume" fill="#6366f1" />
            <Line yAxisId="right" type="monotone" dataKey="fraud_rate" name="Fraud Rate %" stroke="#ef4444" strokeWidth={2} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div style={{ marginTop: "0.6rem" }}>
        <div className="hmi-subtitle">Risk Evolution Timeline</div>
        <input
          type="range"
          min={0}
          max={Math.max(0, timelineLayer.length - 1)}
          value={Math.min(timelineIndex, Math.max(0, timelineLayer.length - 1))}
          onChange={(event) => setTimelineIndex(Number(event.target.value))}
          style={{ width: "100%", marginTop: "0.45rem" }}
        />
        <p style={{ marginTop: "0.35rem", fontSize: "0.8rem", color: "var(--muted)" }}>
          {selectedPoint
            ? `${selectedPoint.date}: volume ${selectedPoint.transaction_volume}, fraud rate ${selectedPoint.fraud_rate}%`
            : "No timeline points available"}
        </p>
      </div>

      <div style={{ marginTop: "0.6rem", fontSize: "0.82rem", color: "var(--muted)" }}>
        Velocity layer points: {layers.velocity_risk_layer?.length || 0} | Amount deviation zones: {layers.amount_deviation_layer?.length || 0} |
        Cross-border signals: {layers.cross_border_fraud_layer?.length || 0}
      </div>

      <hr style={{ borderColor: "rgba(148,163,184,0.22)", margin: "0.9rem 0" }} />

      <h3 className="hmi-title" style={{ margin: 0, fontSize: "0.95rem" }}>Compliance Snapshot</h3>
      <div className="hmi-kpi-grid" style={{ marginTop: "0.55rem" }}>
        <div className="hmi-kpi">
          <span className="hmi-subtitle">Suspicious Txns</span>
          <span className="hmi-kpi-value">{compliance?.suspicious_transactions ?? 0}</span>
        </div>
        <div className="hmi-kpi">
          <span className="hmi-subtitle">Fraud Rate</span>
          <span className="hmi-kpi-value">{compliance?.fraud_rate ?? 0}%</span>
        </div>
      </div>
      <p style={{ marginTop: "0.55rem", fontSize: "0.84rem", lineHeight: 1.4 }}>
        {compliance?.executive_summary || "Compliance report is unavailable for selected period."}
      </p>
    </section>
  );
}
