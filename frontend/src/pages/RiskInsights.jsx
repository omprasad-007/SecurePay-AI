import React, { useEffect, useMemo, useState } from "react";
import { apiFetch } from "../utils/api";
import { getTransactions } from "../utils/fraudUtils";

function scoreColor(score) {
  if (score <= 30) return "#16a34a";
  if (score <= 60) return "#d97706";
  if (score <= 80) return "#ea580c";
  return "#dc2626";
}

function riskBadge(level) {
  const normalized = String(level || "").toLowerCase();
  if (normalized === "low") return "badge badge-low";
  if (normalized === "medium") return "badge badge-medium";
  return "badge badge-high";
}

function encodeHistoryPayload(transactions) {
  if (!Array.isArray(transactions) || transactions.length === 0) return "";

  let sample = transactions
    .slice()
    .sort((a, b) => new Date(a.timestamp || 0).getTime() - new Date(b.timestamp || 0).getTime())
    .slice(-80)
    .map((tx) => ({
      id: tx.id,
      userId: tx.userId,
      receiverId: tx.receiverId,
      merchant: tx.merchant,
      amount: tx.amount,
      deviceId: tx.deviceId,
      ip: tx.ip,
      timestamp: tx.timestamp,
      location: tx.location,
      finalScore: tx.finalScore,
      riskLevel: tx.riskLevel,
      features: tx.features || {}
    }));

  while (sample.length > 0) {
    const json = JSON.stringify(sample);
    const bytes = new TextEncoder().encode(json);
    let binary = "";
    bytes.forEach((value) => {
      binary += String.fromCharCode(value);
    });
    const encoded = btoa(binary)
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/g, "");

    if (encoded.length <= 5500 || sample.length <= 10) {
      return encoded;
    }
    sample = sample.slice(Math.floor(sample.length * 0.75));
  }

  return "";
}

function CircularRiskMeter({ score }) {
  const clamped = Math.max(0, Math.min(100, Number(score || 0)));
  const radius = 64;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;
  const color = scoreColor(clamped);

  return (
    <div className="flex items-center justify-center">
      <svg width="170" height="170" viewBox="0 0 170 170" role="img" aria-label={`Overall risk ${clamped}`}>
        <circle cx="85" cy="85" r={radius} fill="none" stroke="rgba(148, 163, 184, 0.3)" strokeWidth="14" />
        <circle
          cx="85"
          cy="85"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 85 85)"
          style={{ transition: "stroke-dashoffset 0.8s ease, stroke 0.8s ease" }}
        />
        <text x="85" y="83" textAnchor="middle" className="fill-current" style={{ fontSize: "34px", fontWeight: 700 }}>
          {Math.round(clamped)}
        </text>
        <text x="85" y="106" textAnchor="middle" className="fill-current text-sm" style={{ color: "var(--muted)" }}>
          Risk
        </text>
      </svg>
    </div>
  );
}

export default function RiskInsights({ user }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [overview, setOverview] = useState(null);

  useEffect(() => {
    let active = true;

    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const history = getTransactions();
        const encoded = encodeHistoryPayload(history);
        const path = encoded ? `/risk/overview?history=${encodeURIComponent(encoded)}` : "/risk/overview";
        const response = await apiFetch(path, { method: "GET" });
        if (!active) return;
        setOverview(response);
      } catch (err) {
        if (!active) return;
        setError(err.message || "Unable to load risk insights");
      } finally {
        if (active) setLoading(false);
      }
    };

    load();
    window.addEventListener("transactions-updated", load);
    return () => {
      active = false;
      window.removeEventListener("transactions-updated", load);
    };
  }, [user?.uid]);

  const emptyState = useMemo(() => {
    if (!overview) return false;
    return Number(overview.overall_risk_score || 0) === 0 && !!overview.message;
  }, [overview]);

  if (loading) {
    return (
      <div className="card p-8 text-center">
        <p className="text-sm text-muted">Calculating account risk insights...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card p-8">
        <p className="text-red-500 font-medium">{error}</p>
      </div>
    );
  }

  if (emptyState) {
    return (
      <div className="card p-8">
        <h2 className="text-2xl font-semibold mb-2">Risk Insights</h2>
        <p className="text-sm text-muted">No transactions found. Add transactions to generate risk profile.</p>
      </div>
    );
  }

  const score = Number(overview?.overall_risk_score || 0);
  const level = overview?.overall_risk_level || "Low";
  const confidence = Number(overview?.confidence || 0);
  const parameters = Array.isArray(overview?.parameters) ? overview.parameters : [];
  const highRiskTransactions = Array.isArray(overview?.high_risk_transactions) ? overview.high_risk_transactions : [];

  return (
    <div className="space-y-6">
      <section className="card p-6 md:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="grid gap-5 md:grid-cols-[190px_1fr] md:items-center w-full">
            <CircularRiskMeter score={score} />
            <div className="space-y-3">
              <div className="flex items-center gap-3 flex-wrap">
                <h2 className="text-2xl font-semibold">Overall Account Risk</h2>
                <span className={riskBadge(level)}>{level}</span>
              </div>
              <p className="text-sm text-muted">Confidence: <span className="font-semibold" style={{ color: "var(--text)" }}>{Math.round(confidence)}%</span></p>
              <p className="text-sm text-muted">
                Last calculated: {overview?.last_calculated_at ? new Date(overview.last_calculated_at).toLocaleString() : "-"}
              </p>
              <div className="rounded-2xl p-4" style={{ background: "linear-gradient(120deg, rgba(79,70,229,0.12), rgba(34,211,238,0.12))" }}>
                <p className="font-medium">{overview?.summary_explanation || "Risk profile available."}</p>
                <p className="text-sm text-muted mt-2">{overview?.detailed_explanation || ""}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="card p-6 md:p-8">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-semibold">Risk Parameter Breakdown</h3>
          <p className="text-sm text-muted">Weighted contribution overview</p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {parameters.map((param) => {
            const scoreValue = Number(param.score || 0);
            const contribution = Math.max(0, Math.min(100, Number(param.contribution || 0)));
            const barColor = scoreColor(scoreValue);

            return (
              <article key={param.name} className="rounded-2xl border border-slate-200/40 p-4" style={{ background: "var(--card)" }}>
                <div className="flex items-center justify-between gap-3 mb-2">
                  <p className="font-semibold">{param.name}</p>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="badge badge-medium">{Math.round(scoreValue)}</span>
                    <span className="text-muted">W: {Number(param.weight || 0).toFixed(0)}%</span>
                  </div>
                </div>
                <p className="text-xs text-muted mb-2">Contribution: {contribution.toFixed(1)}%</p>
                <div className="h-2 w-full rounded-full bg-slate-200/50 overflow-hidden mb-3">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${contribution}%`, background: barColor, transition: "width 0.5s ease" }}
                  />
                </div>
                <p className="text-sm text-muted">{param.detailed_explanation}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section className="card p-6 md:p-8">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-semibold">High Risk Transactions</h3>
          <p className="text-sm text-muted">Transactions with risk score above 60</p>
        </div>

        {!highRiskTransactions.length && (
          <div className="rounded-2xl border border-slate-200/40 p-4">
            <p className="text-sm text-muted">No high-risk transactions found for the current profile.</p>
          </div>
        )}

        <div className="space-y-3">
          {highRiskTransactions.map((tx) => (
            <article key={tx.transaction_id} className="rounded-2xl border border-slate-200/40 p-4">
              <div className="grid gap-3 md:grid-cols-6 text-sm">
                <div>
                  <p className="text-xs text-muted">Transaction ID</p>
                  <p className="font-medium break-all">{tx.transaction_id}</p>
                </div>
                <div>
                  <p className="text-xs text-muted">Merchant</p>
                  <p className="font-medium">{tx.merchant}</p>
                </div>
                <div>
                  <p className="text-xs text-muted">Amount</p>
                  <p className="font-medium">INR {Number(tx.amount || 0).toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-xs text-muted">Location</p>
                  <p className="font-medium">{tx.location}</p>
                </div>
                <div>
                  <p className="text-xs text-muted">Risk Score</p>
                  <p className="font-medium">{Number(tx.risk_score || 0).toFixed(1)}</p>
                </div>
                <div>
                  <p className="text-xs text-muted">Risk Level</p>
                  <span className={riskBadge(tx.risk_level)}>{tx.risk_level}</span>
                </div>
              </div>

              <details className="mt-4 rounded-xl border border-slate-200/40 bg-slate-50/40 p-3">
                <summary className="cursor-pointer font-medium">Why Flagged?</summary>
                <div className="mt-3 space-y-3 text-sm">
                  <div>
                    <p className="text-xs text-muted mb-1">Top Contributing Factors</p>
                    <div className="flex flex-wrap gap-2">
                      {(tx.why_flagged?.top_factors || []).slice(0, 3).map((factor) => (
                        <span key={factor.name} className="badge badge-medium">
                          {factor.name} ({Number(factor.contribution || 0).toFixed(1)})
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <p className="text-xs text-muted mb-2">Parameter Breakdown</p>
                    <div className="space-y-2">
                      {(tx.why_flagged?.parameter_breakdown || []).map((param) => (
                        <div key={`${tx.transaction_id}-${param.name}`}>
                          <div className="flex items-center justify-between text-xs">
                            <span>{param.name}</span>
                            <span>{Number(param.contribution || 0).toFixed(1)}%</span>
                          </div>
                          <div className="h-1.5 w-full rounded-full bg-slate-200/50 overflow-hidden">
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${Math.max(0, Math.min(100, Number(param.contribution || 0)))}%`,
                                background: scoreColor(Number(param.score || 0))
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <p className="text-xs text-muted">Model Confidence: {Math.round(Number(tx.why_flagged?.model_confidence || 0))}%</p>
                </div>
              </details>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
