import React from "react";

export default function FraudScoreCard({ score = 0, label = "Overall Risk" }) {
  const safeScore = Math.max(0, Math.min(100, score));
  const color = safeScore > 70 ? "var(--danger)" : safeScore > 40 ? "var(--warning)" : "var(--success)";

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted">{label}</p>
          <h3 className="text-3xl font-semibold" style={{ color }}>{safeScore.toFixed(1)}%</h3>
        </div>
        <div className="w-24 h-24 rounded-full border-8 border-slate-100 flex items-center justify-center">
          <div
            className="w-20 h-20 rounded-full flex items-center justify-center text-sm font-semibold"
            style={{ border: `6px solid ${color}` }}
          >
            {safeScore.toFixed(0)}
          </div>
        </div>
      </div>
      <div className="mt-4 h-2 rounded-full bg-slate-100">
        <div className="h-2 rounded-full" style={{ width: `${safeScore}%`, background: color }} />
      </div>
      <p className="text-xs text-muted mt-3">
        Weighted score from anomaly (40%), supervised (40%), graph risk (20%).
      </p>
    </div>
  );
}
