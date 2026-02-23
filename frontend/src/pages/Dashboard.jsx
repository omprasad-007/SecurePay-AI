import React, { useEffect, useState } from "react";
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, BarChart, Bar } from "recharts";
import FraudScoreCard from "../components/FraudScoreCard.jsx";
import TransactionTable from "../components/TransactionTable.jsx";
import GraphView from "../components/GraphView.jsx";
import { buildGraph, getStats, seedTransactions, summarizeRiskSeries } from "../utils/fraudUtils";

export default function Dashboard() {
  const [transactions, setTransactions] = useState([]);

  useEffect(() => {
    const refresh = () => setTransactions(seedTransactions());
    refresh();
    window.addEventListener("transactions-updated", refresh);
    return () => window.removeEventListener("transactions-updated", refresh);
  }, []);

  const stats = getStats(transactions);
  const series = summarizeRiskSeries(transactions);
  const graph = buildGraph(transactions);
  const avgScore = transactions.length
    ? transactions.reduce((acc, tx) => acc + (tx.finalScore || 0), 0) / transactions.length
    : 0;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="card p-6">
          <p className="text-sm text-muted">Total Transactions</p>
          <h2 className="text-3xl font-semibold">{stats.total}</h2>
        </div>
        <div className="card p-6">
          <p className="text-sm text-muted">High Risk Alerts</p>
          <h2 className="text-3xl font-semibold">{stats.highRisk}</h2>
        </div>
        <div className="card p-6">
          <p className="text-sm text-muted">Fraud Rate</p>
          <h2 className="text-3xl font-semibold">{stats.fraudRate}%</h2>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <FraudScoreCard score={avgScore} />
        <div className="card p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Live Risk Trend</h3>
            <span className="text-sm text-muted">Last 10 transactions</span>
          </div>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={series}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.3)" />
                <XAxis dataKey="name" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip />
                <Line type="monotone" dataKey="score" stroke="#6366f1" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Amount Distribution</h3>
            <span className="text-sm text-muted">UPI velocity</span>
          </div>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={series}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.3)" />
                <XAxis dataKey="name" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip />
                <Bar dataKey="amount" fill="#22d3ee" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <GraphView graph={graph} />
      </div>

      <TransactionTable transactions={transactions.slice(0, 6)} />
    </div>
  );
}
