import React from "react";

function badgeClass(level) {
  const normalized = String(level || "").toLowerCase();
  if (normalized === "low") return "badge badge-low";
  if (normalized === "medium") return "badge badge-medium";
  return "badge badge-high";
}

export default function FlaggedTransactionsPanel({ transactions }) {
  const rows = Array.isArray(transactions) ? transactions : [];

  return (
    <section className="card ai-plugin-card space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Per Transaction Risk Explanation</h3>
        <span className="ai-plugin-subtle">{rows.length} flagged</span>
      </div>

      {!rows.length && <p className="ai-plugin-subtle">No flagged transactions in selected date range.</p>}

      {!!rows.length && (
        <div className="ai-table-wrap">
          <table className="ai-table">
            <thead>
              <tr>
                <th>Transaction ID</th>
                <th>Amount</th>
                <th>Risk Score</th>
                <th>Risk Level</th>
                <th>Risk Reasons</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 120).map((row) => (
                <tr key={row.transaction_id}>
                  <td>{row.transaction_id}</td>
                  <td>{Number(row.transaction_amount || 0).toLocaleString()}</td>
                  <td>{Number(row.risk_score || 0).toFixed(2)}</td>
                  <td>
                    <span className={badgeClass(row.risk_level)}>{row.risk_level}</span>
                  </td>
                  <td>
                    {(Array.isArray(row.risk_reasons) ? row.risk_reasons : [])
                      .slice(0, 5)
                      .map((reason, index) => (
                        <span key={`${row.transaction_id}-${index}`} className="inline-block mr-1 mb-1 badge badge-medium">
                          {reason}
                        </span>
                      ))}
                  </td>
                  <td>{row.transaction_datetime ? new Date(row.transaction_datetime).toLocaleString() : "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
