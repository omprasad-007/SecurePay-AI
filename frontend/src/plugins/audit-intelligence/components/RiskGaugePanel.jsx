import React from "react";

function gaugeColor(score) {
  if (score <= 30) return "#16a34a";
  if (score <= 60) return "#d97706";
  if (score <= 80) return "#ea580c";
  return "#dc2626";
}

function gaugeLabel(score) {
  if (score <= 30) return "Low";
  if (score <= 60) return "Medium";
  if (score <= 80) return "High";
  return "Critical";
}

export default function RiskGaugePanel({ intelligence }) {
  const score = Math.max(0, Math.min(100, Number(intelligence?.overall_risk_score || 0)));
  const color = gaugeColor(score);
  const level = intelligence?.risk_classification || gaugeLabel(score);
  const radius = 68;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <section className="card ai-plugin-card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold">Overall Risk Gauge</h3>
        <span className="badge badge-medium">{level}</span>
      </div>

      <div className="flex flex-col md:flex-row md:items-center md:gap-6">
        <svg className="ai-risk-gauge" viewBox="0 0 180 180" role="img" aria-label={`Overall risk ${score.toFixed(1)}`}>
          <circle cx="90" cy="90" r={radius} className="ai-gauge-track" />
          <circle
            cx="90"
            cy="90"
            r={radius}
            className="ai-gauge-progress"
            stroke={color}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            transform="rotate(-90 90 90)"
          />
          <text x="90" y="88" textAnchor="middle" className="fill-current" style={{ fontSize: "28px", fontWeight: 700 }}>
            {Math.round(score)}
          </text>
          <text x="90" y="108" textAnchor="middle" className="fill-current text-xs">
            Risk
          </text>
        </svg>

        <div className="space-y-2">
          <p className="ai-plugin-subtle">Classification</p>
          <p className="text-xl font-semibold" style={{ color }}>
            {level}
          </p>
          <p className="ai-plugin-subtle">
            High-risk transactions: {Number(intelligence?.high_risk_percentage || 0).toFixed(2)}%
          </p>
        </div>
      </div>
    </section>
  );
}
