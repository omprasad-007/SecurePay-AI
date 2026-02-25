import React from "react";

function distributionRows(distribution = {}) {
  return Object.entries(distribution)
    .map(([level, count]) => ({ level, count: Number(count || 0) }))
    .sort((a, b) => b.count - a.count);
}

export default function UploadResultPanel({ result }) {
  if (!result?.summary) {
    return (
      <section className="card ai-plugin-card">
        <p className="ai-plugin-subtle">Run analyze to view upload summary and stored risk profile.</p>
      </section>
    );
  }

  const summary = result.summary;
  const distribution = distributionRows(summary.risk_level_distribution || {});
  const maxCount = Math.max(1, ...distribution.map((item) => item.count));

  return (
    <section className="card ai-plugin-card space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Analyze & Store Result</h3>
        <p className="ai-plugin-subtle mt-1">{result.message || "Upload processed."}</p>
      </div>

      <div className="ai-plugin-grid ai-plugin-grid-2">
        <article>
          <p className="ai-plugin-subtle">Uploaded Records</p>
          <p className="text-2xl font-semibold">{Number(summary.uploaded_records || 0).toLocaleString()}</p>
        </article>
        <article>
          <p className="ai-plugin-subtle">Stored Records</p>
          <p className="text-2xl font-semibold">{Number(summary.stored_records || 0).toLocaleString()}</p>
        </article>
        <article>
          <p className="ai-plugin-subtle">Flagged Records</p>
          <p className="text-2xl font-semibold">{Number(summary.flagged_records || 0).toLocaleString()}</p>
        </article>
        <article>
          <p className="ai-plugin-subtle">Average Risk Score</p>
          <p className="text-2xl font-semibold">{Number(summary.average_risk_score || 0).toFixed(2)}</p>
        </article>
      </div>

      <div className="space-y-2">
        <p className="font-medium">Risk Distribution</p>
        {distribution.map((item) => (
          <div key={item.level} className="ai-bar-row">
            <span className="w-20 text-sm">{item.level}</span>
            <div className="ai-bar">
              <span style={{ width: `${(item.count / maxCount) * 100}%` }} />
            </div>
            <span className="text-sm">{item.count}</span>
          </div>
        ))}
      </div>

      {result.preview && result.preview.length > 0 && (
        <div className="space-y-2 mt-4 pt-4 border-t border-gray-100">
          <p className="font-medium">Backend Sample Preview (Top 5)</p>
          <div className="overflow-x-auto">
            <table className="ai-plugin-table text-xs">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Merchant</th>
                  <th>Amount</th>
                  <th>Risk Level</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {result.preview.slice(0, 5).map((row, idx) => (
                  <tr key={row.transaction_id || idx}>
                    <td>{String(row.transaction_id || "").slice(0, 8)}...</td>
                    <td>{row.merchant_name}</td>
                    <td>{row.transaction_amount}</td>
                    <td className={`risk-text-${(row.risk_level || "low").toLowerCase()}`}>
                      {row.risk_level}
                    </td>
                    <td>{row.risk_score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
