import React, { useEffect, useState } from "react";
import { getTransactions } from "../services/transactionsApi";

export default function EnterpriseDashboardPage() {
  const [stats, setStats] = useState({ total: 0, flagged: 0, avgRisk: 0 });
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const response = await getTransactions({ page: 1, page_size: 100 });
        const items = response.items || [];
        const total = items.length;
        const flagged = items.filter((item) => item.is_flagged).length;
        const avgRisk = total ? items.reduce((acc, item) => acc + Number(item.risk_score || 0), 0) / total : 0;
        setStats({ total, flagged, avgRisk: Number(avgRisk.toFixed(2)) });
      } catch (err) {
        setError(err.message || "Unable to load dashboard");
      }
    };

    load();
  }, []);

  if (error) {
    return <div className="card p-6 text-red-500">{error}</div>;
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Enterprise Dashboard</h2>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="card p-5"><p className="text-sm text-muted">Transactions</p><p className="text-2xl font-semibold">{stats.total}</p></div>
        <div className="card p-5"><p className="text-sm text-muted">Flagged</p><p className="text-2xl font-semibold">{stats.flagged}</p></div>
        <div className="card p-5"><p className="text-sm text-muted">Average Risk</p><p className="text-2xl font-semibold">{stats.avgRisk}</p></div>
      </div>
    </div>
  );
}
