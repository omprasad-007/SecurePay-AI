import React, { useEffect, useState } from "react";
import SuspiciousAlertsPanel from "../components/SuspiciousAlertsPanel";
import TransactionMap from "../components/TransactionMap";
import { getTransactions } from "../services/transactionsApi";

export default function EnterpriseFraudPage() {
  const [transactions, setTransactions] = useState([]);

  useEffect(() => {
    const load = async () => {
      const response = await getTransactions({ page: 1, page_size: 200, risk_min: 40 });
      setTransactions(response.items || []);
    };
    load();
  }, []);

  return (
    <div className="space-y-4">
      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-2">Fraud Analytics</h2>
        <p className="text-sm text-muted">Real-time suspicious pattern monitoring for your organization.</p>
      </div>
      <SuspiciousAlertsPanel transactions={transactions} />
      <TransactionMap transactions={transactions} />
    </div>
  );
}
