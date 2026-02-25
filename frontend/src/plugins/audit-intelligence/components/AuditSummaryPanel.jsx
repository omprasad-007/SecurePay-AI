import React from "react";

function tone(direction) {
  const normalized = String(direction || "").toUpperCase();
  if (normalized === "UP") return "badge badge-high";
  if (normalized === "DOWN") return "badge badge-low";
  return "badge badge-medium";
}

export default function AuditSummaryPanel({ summary, loading }) {
  if (loading) {
    return (
      <section className="card ai-plugin-card">
        <p className="ai-plugin-subtle">Building AI audit summary...</p>
      </section>
    );
  }

  if (!summary) {
    return (
      <section className="card ai-plugin-card">
        <p className="ai-plugin-subtle">No summary data available for the selected period.</p>
      </section>
    );
  }

  return (
    <section className="card ai-plugin-card space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">AI Audit Summary</h3>
        <span className={tone(summary.risk_trend_direction)}>{summary.risk_trend_direction || "STABLE"}</span>
      </div>

      <div className="ai-plugin-grid ai-plugin-grid-2">
        <article>
          <p className="ai-plugin-subtle">Transaction Volume</p>
          <p className="text-2xl font-semibold">{Number(summary.transaction_volume || 0).toLocaleString()}</p>
        </article>
        <article>
          <p className="ai-plugin-subtle">Fraud Rate</p>
          <p className="text-2xl font-semibold">{Number(summary.fraud_rate || 0).toFixed(2)}%</p>
        </article>
        <article>
          <p className="ai-plugin-subtle">Overall Risk</p>
          <p className="text-2xl font-semibold">{Number(summary.overall_risk_score || 0).toFixed(2)}</p>
        </article>
        <article>
          <p className="ai-plugin-subtle">Volume Change</p>
          <p className="text-2xl font-semibold">{Number(summary.transaction_volume_change_pct || 0).toFixed(2)}%</p>
        </article>
      </div>

      <div className="rounded-xl p-3" style={{ background: "color-mix(in srgb, var(--primary) 9%, var(--card))" }}>
        <p className="font-medium">AI Narrative</p>
        <p className="text-sm mt-2">{summary.ai_summary || "Summary unavailable."}</p>
      </div>
    </section>
  );
}
