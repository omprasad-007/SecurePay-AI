import React from "react";

export default function ExcelSummaryPanel({ summary }) {
  if (!summary) return null;

  return (
    <div className="card p-6">
      <h3 className="text-lg font-semibold mb-3">Excel Analytics Summary</h3>
      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-xl bg-sky-50 p-3">
          <p className="text-xs text-muted">Total Transactions</p>
          <p className="text-xl font-semibold">{summary.total_transactions}</p>
        </div>
        <div className="rounded-xl bg-rose-50 p-3">
          <p className="text-xs text-muted">Fraud Percentage</p>
          <p className="text-xl font-semibold">{summary.fraud_percentage}%</p>
        </div>
        <div className="rounded-xl bg-amber-50 p-3">
          <p className="text-xs text-muted">High Risk Count</p>
          <p className="text-xl font-semibold">{summary.high_risk_count}</p>
        </div>
        <div className="rounded-xl bg-emerald-50 p-3">
          <p className="text-xs text-muted">Average Amount</p>
          <p className="text-xl font-semibold">INR {summary.average_amount}</p>
        </div>
        <div className="rounded-xl bg-indigo-50 p-3">
          <p className="text-xs text-muted">Most Risky Merchant</p>
          <p className="text-xl font-semibold">{summary.most_risky_merchant}</p>
        </div>
        <div className="rounded-xl bg-cyan-50 p-3">
          <p className="text-xs text-muted">Peak Fraud Hour</p>
          <p className="text-xl font-semibold">{summary.peak_fraud_hour}:00</p>
        </div>
      </div>
    </div>
  );
}
