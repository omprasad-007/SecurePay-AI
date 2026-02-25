import React from "react";

function topItems(items, labelKey, valueKey) {
  return (Array.isArray(items) ? items : []).slice(0, 6).map((item, index) => ({
    id: `${item?.[labelKey] || "item"}-${index}`,
    label: String(item?.[labelKey] || "Unknown"),
    value: Number(item?.[valueKey] || 0),
  }));
}

export default function RiskBreakdownPanel({ intelligence }) {
  const users = topItems(intelligence?.top_suspicious_users, "user_id", "average_risk");
  const locations = topItems(intelligence?.high_risk_locations, "city", "high_risk_count");
  const patterns = topItems(intelligence?.common_fraud_patterns, "pattern", "count");

  return (
    <section className="card ai-plugin-card space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Risk Breakdown</h3>
        <span className="ai-plugin-subtle">% high risk: {Number(intelligence?.high_risk_percentage || 0).toFixed(2)}</span>
      </div>

      <div className="ai-plugin-grid ai-plugin-grid-3">
        <article>
          <p className="font-medium mb-2">Top Suspicious Users</p>
          {!users.length && <p className="ai-plugin-subtle">No suspicious users detected.</p>}
          <div className="space-y-2">
            {users.map((item) => (
              <div key={item.id} className="flex items-center justify-between text-sm">
                <span>{item.label}</span>
                <span className="badge badge-medium">{item.value.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </article>

        <article>
          <p className="font-medium mb-2">High-Risk Locations</p>
          {!locations.length && <p className="ai-plugin-subtle">No high-risk locations detected.</p>}
          <div className="space-y-2">
            {locations.map((item) => (
              <div key={item.id} className="flex items-center justify-between text-sm">
                <span>{item.label}</span>
                <span className="badge badge-high">{item.value}</span>
              </div>
            ))}
          </div>
        </article>

        <article>
          <p className="font-medium mb-2">Fraud Patterns</p>
          {!patterns.length && <p className="ai-plugin-subtle">No repeat fraud patterns detected.</p>}
          <div className="space-y-2">
            {patterns.map((item) => (
              <div key={item.id} className="flex items-center justify-between text-sm">
                <span>{item.label}</span>
                <span className="badge badge-medium">{item.value}</span>
              </div>
            ))}
          </div>
        </article>
      </div>
    </section>
  );
}
