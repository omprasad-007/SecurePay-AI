import React from "react";

export default function TransactionTable({ transactions = [] }) {
  return (
    <div className="card p-6 overflow-x-auto">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Live Transactions</h3>
        <span className="text-sm text-muted">{transactions.length} records</span>
      </div>
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left text-muted border-b">
            <th className="py-2">Txn ID</th>
            <th className="py-2">User</th>
            <th className="py-2">Receiver</th>
            <th className="py-2">Amount</th>
            <th className="py-2">Risk</th>
            <th className="py-2">Status</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((tx) => (
            <tr key={tx.id} className="border-b last:border-none">
              <td className="py-3">{tx.id}</td>
              <td className="py-3">{tx.userId}</td>
              <td className="py-3">{tx.receiverId}</td>
              <td className="py-3">₹{tx.amount.toLocaleString()}</td>
              <td className="py-3">{tx.finalScore?.toFixed(1) ?? "-"}%</td>
              <td className="py-3">
                <span
                  className={`badge ${
                    tx.riskLevel === "High" || tx.riskLevel === "HIGH" || tx.riskLevel === "CRITICAL"
                      ? "badge-high"
                      : tx.riskLevel === "Medium" || tx.riskLevel === "MEDIUM"
                      ? "badge-medium"
                      : "badge-low"
                  }`}
                >
                  {tx.riskLevel || "Low"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
