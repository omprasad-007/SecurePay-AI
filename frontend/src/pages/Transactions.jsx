import React, { useEffect, useMemo, useState } from "react";
import TransactionTable from "../components/TransactionTable.jsx";
import RiskBreakdownPanel from "../components/RiskBreakdownPanel.jsx";
import PatternLibrary from "../components/PatternLibrary.jsx";
import { apiFetch } from "../utils/api";
import { addTransaction, createTransaction, getDetectedPatterns, seedTransactions, updateTransaction } from "../utils/fraudUtils";
import { getDeviceFingerprint } from "../utils/deviceFingerprint";
import { canMarkFraud, canOverride } from "../utils/themeManager";

export default function Transactions({ role }) {
  const [transactions, setTransactions] = useState([]);
  const [amount, setAmount] = useState(1200);
  const [receiverId, setReceiverId] = useState("MERCH1");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [latest, setLatest] = useState(null);

  useEffect(() => {
    const refresh = () => {
      const seeded = seedTransactions();
      setTransactions(seeded);
    };
    refresh();
    window.addEventListener("transactions-updated", refresh);
    return () => window.removeEventListener("transactions-updated", refresh);
  }, []);

  const downloadCsv = () => {
    if (!transactions.length) return;
    const headers = ["id", "userId", "receiverId", "amount", "deviceId", "merchant", "timestamp", "finalScore", "riskLevel"];
    const rows = transactions.map((tx) => [tx.id, tx.userId, tx.receiverId, tx.amount, tx.deviceId, tx.merchant, tx.timestamp, tx.finalScore ?? "", tx.riskLevel || ""]);
    const csv = [headers.join(","), ...rows.map((row) => row.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "securepay-demo-transactions.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const submitFeedback = async (label) => {
    if (!latest) return;
    try {
      await apiFetch("/feedback", {
        method: "POST",
        body: JSON.stringify({
          transaction_id: latest.transactionId,
          label,
          score: latest.adaptiveScore
        })
      });
      setError("");
    } catch (err) {
      setError(err.message || "Feedback failed");
    }
  };

  const overrideSafe = () => {
    if (!latest) return;
    const tx = transactions.find((item) => item.id === latest.transactionId);
    if (!tx) return;
    const updated = { ...tx, riskLevel: "LOW", finalScore: 10 };
    const after = updateTransaction(updated);
    setTransactions(after);
  };

  const handleSimulate = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    const device = await getDeviceFingerprint();

    const transaction = createTransaction({ amount: Number(amount), receiverId, deviceId: device.fingerprint.slice(0, 12) });
    const updatedList = addTransaction(transaction);
    setTransactions(updatedList);

    try {
      const response = await apiFetch("/predict", {
        method: "POST",
        body: JSON.stringify({
          transaction: {
            ...transaction,
            deviceFingerprint: device.fingerprint
          },
          history: updatedList.slice(0, 25),
          device_context: { ipRisk: device.ipRisk }
        })
      });

      const enriched = {
        ...transaction,
        finalScore: response.adaptive_score,
        riskLevel: response.adaptive_risk_level,
        features: response.features,
        decisionAction: response.decision_action,
        patterns: response.patterns || []
      };
      const afterUpdate = updateTransaction(enriched);
      setTransactions(afterUpdate);
      setLatest({
        transactionId: transaction.id,
        adaptiveScore: response.adaptive_score,
        adaptiveRiskLevel: response.adaptive_risk_level,
        decisionAction: response.decision_action,
        riskDrivers: response.risk_drivers || [],
        patterns: response.patterns || []
      });
      localStorage.setItem("securepay_last_explanation", response.explanation || "");
    } catch (err) {
      setError(err.message || "Prediction failed");
    } finally {
      setLoading(false);
    }
  };

  const latestPatterns = useMemo(() => {
    if (latest?.patterns?.length) return latest.patterns;
    return getDetectedPatterns();
  }, [latest]);

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-2">Simulate Transaction</h2>
        <p className="text-sm text-muted mb-4">Existing anomaly/supervised/graph pipeline is preserved; adaptive risk and decisioning wrap around it.</p>
        <form className="grid gap-4 md:grid-cols-3" onSubmit={handleSimulate}>
          <div>
            <label className="text-sm text-muted">Amount (INR)</label>
            <input className="w-full border rounded-xl px-4 py-3" type="number" value={amount} onChange={(event) => setAmount(event.target.value)} />
          </div>
          <div>
            <label className="text-sm text-muted">Receiver ID</label>
            <input className="w-full border rounded-xl px-4 py-3" value={receiverId} onChange={(event) => setReceiverId(event.target.value)} />
          </div>
          <div className="flex items-end">
            <button className="btn-primary w-full" type="submit" disabled={loading}>{loading ? "Scoring..." : "Score Transaction"}</button>
          </div>
        </form>
        <div className="flex flex-wrap gap-3 mt-4">
          <button className="btn-outline" type="button" onClick={downloadCsv}>Download Demo CSV</button>
          {canMarkFraud(role) && <button className="btn-outline" type="button" onClick={() => submitFeedback("fraud")}>Mark as Fraud</button>}
          {canMarkFraud(role) && <button className="btn-outline" type="button" onClick={() => submitFeedback("safe")}>Mark as Safe</button>}
          {canOverride(role) && <button className="btn-outline" type="button" onClick={overrideSafe}>Admin Override to LOW</button>}
        </div>
        {error && <p className="text-sm text-red-500 mt-3">{error}</p>}
      </div>

      {latest && (
        <div className="grid gap-4 lg:grid-cols-2">
          <RiskBreakdownPanel
            adaptiveScore={latest.adaptiveScore}
            adaptiveRiskLevel={latest.adaptiveRiskLevel}
            decisionAction={latest.decisionAction}
            riskDrivers={latest.riskDrivers}
          />
          <PatternLibrary patterns={latestPatterns} />
        </div>
      )}

      <TransactionTable transactions={transactions} />
    </div>
  );
}
