import React, { useEffect, useState } from "react";
import AboutEnterpriseContent from "../components/AboutEnterpriseContent.jsx";
import { getDatasetInsights } from "../utils/fraudUtils";

export default function About() {
  const [dataset, setDataset] = useState(() => getDatasetInsights());

  useEffect(() => {
    const refresh = () => setDataset(getDatasetInsights());
    window.addEventListener("transactions-updated", refresh);
    return () => window.removeEventListener("transactions-updated", refresh);
  }, []);

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <h2 className="text-2xl font-semibold mb-2">About SecurePay AI Enterprise</h2>
        <p className="text-sm text-muted">
          Integrated fraud intelligence platform for UPI and digital payments with adaptive AI, graph risk analytics, cybersecurity controls, and explainable decision workflows.
        </p>
      </div>

      {dataset && (
        <div className="card p-6 border border-sky-200">
          <h3 className="text-lg font-semibold mb-2 text-sky-700">About This Dataset</h3>
          <p className="text-sm text-muted">
            This dataset includes transactions across {dataset.unique_users} users with total volume INR {dataset.total_volume}.
            The system detected a {dataset.fraud_detection_rate}% fraud rate using adaptive anomaly detection and graph intelligence.
          </p>
          <div className="grid gap-3 md:grid-cols-4 mt-4 text-sm">
            <div className="rounded-xl bg-slate-100 p-3">Total Users: <b>{dataset.unique_users}</b></div>
            <div className="rounded-xl bg-slate-100 p-3">Merchant Categories: <b>{dataset.merchant_categories}</b></div>
            <div className="rounded-xl bg-slate-100 p-3">Fraud Rate: <b>{dataset.fraud_detection_rate}%</b></div>
            <div className="rounded-xl bg-slate-100 p-3">Business Impact: <b>Improved fraud triage</b></div>
          </div>
        </div>
      )}

      <AboutEnterpriseContent />
    </div>
  );
}

