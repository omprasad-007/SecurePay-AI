import React, { useEffect, useState } from "react";
import { apiFetch } from "../utils/api";
import FraudScoreCard from "../components/FraudScoreCard.jsx";
import GraphView from "../components/GraphView.jsx";
import { buildGraph, getTransactions } from "../utils/fraudUtils";
import { canExport } from "../utils/themeManager";

export default function FraudAnalytics({ role }) {
  const [graph, setGraph] = useState({ nodes: [], links: [] });
  const [summary, setSummary] = useState({ anomaly: 0, supervised: 0, graph: 0 });
  const [message, setMessage] = useState("");

  useEffect(() => {
    const loadAnalytics = async () => {
      const history = getTransactions();
      try {
        const response = await apiFetch("/analytics/graph", {
          method: "POST",
          body: JSON.stringify({ history })
        });
        setGraph(response.graph);
        setSummary(response.summary);
      } catch {
        setGraph(buildGraph(history));
        setSummary({ anomaly: 52, supervised: 61, graph: 38 });
      }
    };

    loadAnalytics();
  }, []);

  const exportReport = async (reportType) => {
    const history = getTransactions();
    try {
      const response = await apiFetch("/reports/export", {
        method: "POST",
        body: JSON.stringify({ history, report_type: reportType })
      });
      if (reportType === "csv") {
        const blob = new Blob([response.csv], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "securepay-suspicious-transactions.csv";
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
      }
      if (reportType === "summary_pdf") {
        const byteChars = atob(response.pdf_base64);
        const byteNumbers = Array.from(byteChars).map((c) => c.charCodeAt(0));
        const blob = new Blob([new Uint8Array(byteNumbers)], { type: "application/pdf" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "securepay-weekly-summary.pdf";
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
      }
      if (reportType === "metrics") {
        setMessage(`Fraud Rate: ${response.summary.fraud_rate}% | High Risk: ${response.summary.high_risk}`);
      }
    } catch (err) {
      setMessage(err.message || "Export failed");
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 lg:grid-cols-3">
        <FraudScoreCard score={summary.anomaly} label="Anomaly Risk" />
        <FraudScoreCard score={summary.supervised} label="Supervised Risk" />
        <FraudScoreCard score={summary.graph} label="Graph Risk" />
      </div>

      {canExport(role) && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-3">Export Compliance Reports</h3>
          <div className="flex flex-wrap gap-3">
            <button className="btn-outline" onClick={() => exportReport("csv")}>Export CSV</button>
            <button className="btn-outline" onClick={() => exportReport("summary_pdf")}>Export Weekly PDF</button>
            <button className="btn-outline" onClick={() => exportReport("metrics")}>Export Metrics</button>
          </div>
          {message && <p className="text-sm text-muted mt-3">{message}</p>}
        </div>
      )}

      <GraphView graph={graph} />
      <div className="card p-6">
        <h3 className="text-lg font-semibold mb-2">Cybersecurity Controls</h3>
        <ul className="text-sm text-muted list-disc pl-5">
          <li>API rate limiting enabled with IP-based throttling.</li>
          <li>JWT/Firebase token verification for protected endpoints.</li>
          <li>Input sanitization and validation for each transaction payload.</li>
          <li>Fraud attempt logging for alert simulation.</li>
        </ul>
      </div>
    </div>
  );
}
