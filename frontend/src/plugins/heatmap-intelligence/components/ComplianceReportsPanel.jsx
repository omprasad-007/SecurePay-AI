import React, { useMemo, useState } from "react";
import { exportComplianceReport } from "../services/heatmapApi";

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export default function ComplianceReportsPanel({ filters, compliance, suspiciousReport, sarReport }) {
  const [exporting, setExporting] = useState("");
  const [error, setError] = useState("");

  const suspiciousPreview = useMemo(
    () => (suspiciousReport?.transactions || []).slice(0, 6),
    [suspiciousReport]
  );
  const sarPreview = useMemo(() => (sarReport?.reports || []).slice(0, 5), [sarReport]);

  const runExport = async (format) => {
    setError("");
    setExporting(format);
    try {
      const blob = await exportComplianceReport({ ...filters, export_format: format });
      const extension = format === "excel" ? "xlsx" : format === "encrypted_xml" ? "xml" : format;
      downloadBlob(blob, `compliance_report.${extension}`);
    } catch (err) {
      setError(err?.message || "Export failed");
    } finally {
      setExporting("");
    }
  };

  return (
    <section className="hmi-panel">
      <h2 className="hmi-title">Bank Compliance Reporting</h2>
      <p className="hmi-subtitle">SAR generation, AML report exports, and investigation-ready suspicious transaction logs.</p>

      <div className="hmi-kpi-grid" style={{ marginTop: "0.8rem" }}>
        <div className="hmi-kpi">
          <span className="hmi-subtitle">Total Transactions</span>
          <span className="hmi-kpi-value">{compliance?.total_transactions ?? 0}</span>
        </div>
        <div className="hmi-kpi">
          <span className="hmi-subtitle">Suspicious Txns</span>
          <span className="hmi-kpi-value">{compliance?.suspicious_transactions ?? 0}</span>
        </div>
        <div className="hmi-kpi">
          <span className="hmi-subtitle">SAR Records</span>
          <span className="hmi-kpi-value">{sarReport?.total_reports ?? 0}</span>
        </div>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.55rem", marginTop: "0.8rem" }}>
        <button className="btn-outline" onClick={() => runExport("pdf")} disabled={!!exporting}>
          {exporting === "pdf" ? "Exporting..." : "Export PDF"}
        </button>
        <button className="btn-outline" onClick={() => runExport("excel")} disabled={!!exporting}>
          {exporting === "excel" ? "Exporting..." : "Export Excel"}
        </button>
        <button className="btn-outline" onClick={() => runExport("json")} disabled={!!exporting}>
          {exporting === "json" ? "Exporting..." : "Export JSON"}
        </button>
        <button className="btn-outline" onClick={() => runExport("encrypted_xml")} disabled={!!exporting}>
          {exporting === "encrypted_xml" ? "Exporting..." : "Export Encrypted XML"}
        </button>
      </div>

      {error && <p style={{ marginTop: "0.6rem", color: "#ef4444", fontSize: "0.82rem" }}>{error}</p>}

      <h3 className="hmi-title" style={{ marginTop: "1rem", marginBottom: "0.45rem", fontSize: "0.95rem" }}>Suspicious Transaction Report</h3>
      <div className="hmi-table-wrap">
        <table className="hmi-table">
          <thead>
            <tr>
              <th>Transaction</th>
              <th>User</th>
              <th>Risk</th>
              <th>Cluster</th>
              <th>Device</th>
            </tr>
          </thead>
          <tbody>
            {suspiciousPreview.map((row) => (
              <tr key={row.transaction_id}>
                <td>{row.transaction_id}</td>
                <td>{row.user_details?.user_id}</td>
                <td>{row.risk_score}</td>
                <td>{row.fraud_cluster_id || "-"}</td>
                <td>{row.device_fingerprint || "-"}</td>
              </tr>
            ))}
            {!suspiciousPreview.length && (
              <tr>
                <td colSpan={5} className="text-muted">No suspicious transactions for current filters.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <h3 className="hmi-title" style={{ marginTop: "1rem", marginBottom: "0.45rem", fontSize: "0.95rem" }}>SAR Records</h3>
      <div className="hmi-table-wrap">
        <table className="hmi-table">
          <thead>
            <tr>
              <th>Report ID</th>
              <th>Subject</th>
              <th>Risk</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {sarPreview.map((row) => (
              <tr key={row.report_id}>
                <td>{row.report_id}</td>
                <td>{row.subject_account}</td>
                <td>{row.risk_score}</td>
                <td>{row.compliance_status}</td>
              </tr>
            ))}
            {!sarPreview.length && (
              <tr>
                <td colSpan={4} className="text-muted">No SAR candidates generated.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
