import React, { useCallback, useEffect, useMemo, useState } from "react";
import "../styles.css";
import { useAuditFilters } from "../hooks/useAuditFilters";
import { getAuditAlerts, getAuditCompare, getAuditSummary, getRiskIntelligence } from "../services/auditApi";
import AuditFilterPanel from "../components/AuditFilterPanel";
import AuditAlertsPanel from "../components/AuditAlertsPanel";
import AuditSummaryPanel from "../components/AuditSummaryPanel";
import RiskGaugePanel from "../components/RiskGaugePanel";
import RiskBreakdownPanel from "../components/RiskBreakdownPanel";
import CompareAnalyticsPanel from "../components/CompareAnalyticsPanel";
import FlaggedTransactionsPanel from "../components/FlaggedTransactionsPanel";

export default function RiskIntelligencePage() {
  const { filters, normalizedFilters, setField, apply, reset, refreshKey } = useAuditFilters();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [intelligence, setIntelligence] = useState(null);
  const [summary, setSummary] = useState(null);
  const [compare, setCompare] = useState(null);
  const [alerts, setAlerts] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [riskData, summaryData, compareData, alertData] = await Promise.all([
        getRiskIntelligence(normalizedFilters),
        getAuditSummary(normalizedFilters),
        getAuditCompare(normalizedFilters),
        getAuditAlerts({ ...normalizedFilters, limit: 50 }),
      ]);
      setIntelligence(riskData);
      setSummary(summaryData);
      setCompare(compareData);
      setAlerts(alertData);
    } catch (err) {
      setError(err?.message || "Failed to load risk intelligence.");
    } finally {
      setLoading(false);
    }
  }, [normalizedFilters]);

  useEffect(() => {
    loadData();
  }, [loadData, refreshKey]);

  useEffect(() => {
    const listener = () => apply();
    window.addEventListener("audit-intelligence-updated", listener);
    return () => window.removeEventListener("audit-intelligence-updated", listener);
  }, [apply]);

  const highRiskDetected = useMemo(() => {
    const score = Number(intelligence?.overall_risk_score || 0);
    const highRiskPct = Number(intelligence?.high_risk_percentage || 0);
    const alertsList = Array.isArray(alerts?.alerts) ? alerts.alerts : [];
    const fromAlerts = alertsList.some((item) => String(item.title || "").toLowerCase().includes("high risk audit"));
    return fromAlerts || score > 70 || highRiskPct > 25;
  }, [alerts?.alerts, intelligence?.high_risk_percentage, intelligence?.overall_risk_score]);

  return (
    <div className="space-y-4">
      <div className="card" style={{ padding: "1rem 1.1rem" }}>
        <h1 style={{ margin: 0, fontSize: "1.35rem", fontWeight: 700 }}>Risk Intelligence</h1>
        <p className="text-muted" style={{ marginTop: "0.35rem" }}>
          Overall risk scoring, transaction-level explanations, comparative analytics, and auto-alert monitoring.
        </p>
      </div>

      {highRiskDetected && (
        <div className="ai-alert">
          <strong>High Risk Audit Detected:</strong> risk threshold exceeded for current audit window.
        </div>
      )}
      {error && (
        <div className="ai-alert">
          <strong>Error:</strong> {error}
        </div>
      )}

      <div className="ai-plugin-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))" }}>
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
          <AuditSummaryPanel summary={summary} loading={loading} />
        </div>

        <div className="ai-plugin-grid">
          <RiskGaugePanel intelligence={intelligence} />
          <RiskBreakdownPanel intelligence={intelligence} />
          <CompareAnalyticsPanel compare={compare} />
          <FlaggedTransactionsPanel transactions={intelligence?.flagged_transactions || []} />
        </div>
      </div>
    </div>
  );
}
