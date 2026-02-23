import React from "react";

function ListCard({ title, data = [] }) {
  return (
    <div className="rounded-xl border border-slate-200 p-4">
      <p className="text-sm font-semibold mb-2">{title}</p>
      <div className="space-y-1 text-sm">
        {data.length === 0 && <p className="text-muted">No data</p>}
        {data.map((item) => (
          <div key={item.id} className="flex items-center justify-between">
            <span>{item.id}</span>
            <span className="font-medium">{item.score}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function DatasetInsights({ insights }) {
  if (!insights) return null;

  return (
    <div className="card p-6 space-y-4">
      <h3 className="text-lg font-semibold">AI-Enhanced Dataset Insights</h3>
      <div className="grid gap-3 md:grid-cols-4 text-sm">
        <div className="rounded-xl bg-slate-100 p-3">Unique Users: <b>{insights.unique_users}</b></div>
        <div className="rounded-xl bg-slate-100 p-3">Total Volume: <b>INR {insights.total_volume}</b></div>
        <div className="rounded-xl bg-slate-100 p-3">Merchant Categories: <b>{insights.merchant_categories}</b></div>
        <div className="rounded-xl bg-slate-100 p-3">Fraud Detection Rate: <b>{insights.fraud_detection_rate}%</b></div>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <ListCard title="Top 5 Risky Users" data={insights.top_risky_users} />
        <ListCard title="Top 5 Risky Merchants" data={insights.top_risky_merchants} />
        <ListCard title="Top 5 Risky Devices" data={insights.top_risky_devices} />
      </div>
    </div>
  );
}
