import React, { useMemo, useState } from "react";
import { deleteTransaction, exportTransactions, getTransactions } from "../services/transactionsApi";
import { can } from "../rbac/permissions";
import { useEnterpriseAuth } from "../hooks/useEnterpriseAuth";
import { downloadBlob } from "../utils";

export default function EnterpriseTransactionsPage() {
  const { role } = useEnterpriseAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [merchant, setMerchant] = useState("");
  const [error, setError] = useState("");

  const canDelete = useMemo(() => can(role, "DELETE_TRANSACTION"), [role]);

  const fetchRows = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await getTransactions({ page: 1, page_size: 50, merchant });
      setItems(response.items || []);
    } catch (err) {
      setError(err.message || "Failed to load transactions");
    } finally {
      setLoading(false);
    }
  };

  const removeRow = async (transactionId) => {
    await deleteTransaction(transactionId);
    await fetchRows();
  };

  const downloadFraudOnly = async () => {
    const blob = await exportTransactions({ format: "csv", fraud_only: true });
    downloadBlob(blob, "fraud_transactions.csv");
  };

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Transactions</h2>
      <div className="card p-4 flex flex-wrap gap-3 items-end">
        <div>
          <label className="text-xs text-muted">Merchant</label>
          <input className="w-full border rounded-xl px-3 py-2" value={merchant} onChange={(e) => setMerchant(e.target.value)} />
        </div>
        <button className="btn-primary" onClick={fetchRows} disabled={loading}>{loading ? "Loading..." : "Search"}</button>
        <button className="btn-outline" onClick={downloadFraudOnly}>Export Fraud CSV</button>
      </div>

      {error && <div className="text-sm text-red-500">{error}</div>}

      <div className="card p-4 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-muted">
              <th className="py-2">ID</th>
              <th className="py-2">Merchant</th>
              <th className="py-2">Amount</th>
              <th className="py-2">Risk</th>
              <th className="py-2">Status</th>
              {canDelete && <th className="py-2">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.transaction_id} className="border-t border-slate-200/30">
                <td className="py-2">{item.transaction_id}</td>
                <td className="py-2">{item.merchant_name}</td>
                <td className="py-2">{item.currency} {item.transaction_amount}</td>
                <td className="py-2">{item.risk_score}</td>
                <td className="py-2">{item.transaction_status}</td>
                {canDelete && (
                  <td className="py-2">
                    <button className="btn-outline" onClick={() => removeRow(item.transaction_id)}>Delete</button>
                  </td>
                )}
              </tr>
            ))}
            {!items.length && (
              <tr>
                <td className="py-4 text-muted" colSpan={canDelete ? 6 : 5}>No transactions</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
