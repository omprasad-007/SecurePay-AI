import React from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  Bar,
  Line,
} from "recharts";

function toChartData(compare) {
  const line = Array.isArray(compare?.chart?.line) ? compare.chart.line : [];
  const bar = Array.isArray(compare?.chart?.bar) ? compare.chart.bar : [];
  const byLabel = new Map();

  line.forEach((item) => {
    byLabel.set(item.label, {
      label: item.label,
      fraud_rate: Number(item.fraud_rate || 0),
      risk_score: Number(item.risk_score || 0),
      volume: 0,
    });
  });
  bar.forEach((item) => {
    const current = byLabel.get(item.label) || { label: item.label, fraud_rate: 0, risk_score: 0, volume: 0 };
    current.volume = Number(item.volume || 0);
    byLabel.set(item.label, current);
  });

  return Array.from(byLabel.values());
}

export default function CompareAnalyticsPanel({ compare }) {
  const data = toChartData(compare);
  const delta = compare?.delta || {};

  return (
    <section className="card ai-plugin-card space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Compare With Previous Period</h3>
        <span className="ai-plugin-subtle">Auto previous window</span>
      </div>

      <div className="ai-plugin-grid ai-plugin-grid-3">
        <article>
          <p className="ai-plugin-subtle">Volume Change</p>
          <p className="text-xl font-semibold">{Number(delta.volume_change_pct || 0).toFixed(2)}%</p>
        </article>
        <article>
          <p className="ai-plugin-subtle">Fraud Rate Change</p>
          <p className="text-xl font-semibold">{Number(delta.fraud_rate_change_pct || 0).toFixed(2)}%</p>
        </article>
        <article>
          <p className="ai-plugin-subtle">Risk Score Change</p>
          <p className="text-xl font-semibold">{Number(delta.risk_score_change_pct || 0).toFixed(2)}%</p>
        </article>
      </div>

      <div style={{ width: "100%", height: "280px" }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.3)" />
            <XAxis dataKey="label" stroke="#94a3b8" />
            <YAxis yAxisId="left" stroke="#94a3b8" />
            <YAxis yAxisId="right" orientation="right" stroke="#94a3b8" />
            <Tooltip />
            <Legend />
            <Bar yAxisId="left" dataKey="volume" fill="#22d3ee" name="Transaction Volume" radius={[6, 6, 0, 0]} />
            <Line yAxisId="right" type="monotone" dataKey="fraud_rate" stroke="#ef4444" strokeWidth={2} name="Fraud Rate %" />
            <Line yAxisId="right" type="monotone" dataKey="risk_score" stroke="#6366f1" strokeWidth={2} name="Risk Score" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
