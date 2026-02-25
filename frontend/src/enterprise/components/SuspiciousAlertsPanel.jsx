import React from "react";

export default function SuspiciousAlertsPanel({ transactions = [] }) {
  const suspiciousLocations = transactions.filter((tx) => Number(tx.risk_score || 0) >= 80 && tx.city);
  const suspiciousMerchants = transactions.filter((tx) => Number(tx.risk_score || 0) >= 80 && tx.merchant_name);

  return (
    <div className="card p-4">
      <h3 className="font-semibold mb-3">Suspicious Alerts</h3>
      <div className="grid gap-3 md:grid-cols-2 text-sm">
        <div>
          <p className="text-xs text-muted mb-2">Location Alerts</p>
          {suspiciousLocations.slice(0, 5).map((tx) => (
            <p key={`loc-${tx.transaction_id}`} className="mb-1">{tx.city} ({tx.risk_score})</p>
          ))}
          {!suspiciousLocations.length && <p className="text-muted">No suspicious location alerts.</p>}
        </div>
        <div>
          <p className="text-xs text-muted mb-2">Merchant Alerts</p>
          {suspiciousMerchants.slice(0, 5).map((tx) => (
            <p key={`mer-${tx.transaction_id}`} className="mb-1">{tx.merchant_name} ({tx.risk_score})</p>
          ))}
          {!suspiciousMerchants.length && <p className="text-muted">No suspicious merchant alerts.</p>}
        </div>
      </div>
    </div>
  );
}
