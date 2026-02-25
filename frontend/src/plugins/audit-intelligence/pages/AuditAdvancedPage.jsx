import React, { useCallback, useEffect, useState } from "react";
import "../styles.css";
import { useAuditFilters } from "../hooks/useAuditFilters";
import {
  downloadAuditExport,
  getAuditAlerts,
  getAuditSummary,
  saveBlobAsFile,
  sendAuditEmailReport,
} from "../services/auditApi";
import AuditFilterPanel from "../components/AuditFilterPanel";
import AuditExportPanel from "../components/AuditExportPanel";
import AuditSummaryPanel from "../components/AuditSummaryPanel";
import AuditAlertsPanel from "../components/AuditAlertsPanel";

export default function AuditAdvancedPage() {
  const { filters, normalizedFilters, setField, apply, reset, refreshKey } = useAuditFilters();
  const [format, setFormat] = useState("pdf");
  const [email, setEmail] = useState("");
  const [summary, setSummary] = useState(null);
  const [alerts, setAlerts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [sendingEmail, setSendingEmail] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [summaryData, alertsData] = await Promise.all([
        getAuditSummary(normalizedFilters),
        getAuditAlerts({ ...normalizedFilters, limit: 50 }),
      ]);
      setSummary(summaryData);
      setAlerts(alertsData);
    } catch (err) {
      setError(err?.message || "Failed to load audit intelligence data.");
    } finally {
      setLoading(false);
    }
  }, [normalizedFilters]);

  useEffect(() => {
    loadData();
  }, [loadData, refreshKey]);

  const handleDownload = async () => {
    setDownloading(true);
    setError("");
    setMessage("");
    try {
      const exported = await downloadAuditExport({ ...normalizedFilters, format });
      saveBlobAsFile(exported.blob, exported.filename);
      setMessage(`Report downloaded: ${exported.filename}`);
    } catch (err) {
      setError(err?.message || "Failed to export audit report.");
    } finally {
      setDownloading(false);
    }
  };

  const handleSendEmail = async () => {
    setSendingEmail(true);
    setError("");
    setMessage("");
    try {
      const response = await sendAuditEmailReport({
        start_date: normalizedFilters.start_date,
        end_date: normalizedFilters.end_date,
        email,
      });
      setMessage(`Email report status: ${response.status} (${response.email})`);
    } catch (err) {
      setError(err?.message || "Failed to send audit report email.");
    } finally {
      setSendingEmail(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="card" style={{ padding: "1rem 1.1rem" }}>
        <h1 style={{ margin: 0, fontSize: "1.35rem", fontWeight: 700 }}>Advanced Audit Section</h1>
        <p className="text-muted" style={{ marginTop: "0.35rem" }}>
          Enterprise audit export with risk/status/user filters, AI summary generation, and compliance alert feed.
        </p>
      </div>

      {error && (
        <div className="ai-alert">
          <strong>Error:</strong> {error}
        </div>
      )}
      {message && (
        <div className="card ai-plugin-card">
          <p className="text-sm text-emerald-600">{message}</p>
        </div>
      )}

      <div className="ai-plugin-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))" }}>
        <div className="ai-plugin-grid">
          <AuditFilterPanel
            filters={filters}
            onChange={setField}
            onApply={apply}
            onReset={() => {
              reset();
              setTimeout(() => apply(), 0);
            }}
            loading={loading}
          />
          <AuditAlertsPanel alerts={alerts} loading={loading} />
        </div>

        <div className="ai-plugin-grid">
          <AuditExportPanel
            format={format}
            onFormatChange={setFormat}
            onDownload={handleDownload}
            downloading={downloading}
            email={email}
            onEmailChange={setEmail}
            onSendEmail={handleSendEmail}
            sendingEmail={sendingEmail}
          />
          <AuditSummaryPanel summary={summary} loading={loading} />
        </div>
      </div>
    </div>
  );
}
