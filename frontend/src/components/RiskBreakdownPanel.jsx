import React from "react";

export default function RiskBreakdownPanel({ adaptiveScore, adaptiveRiskLevel, decisionAction, riskDrivers = [] }) {
  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Explainable AI 2.0</h3>
        <span className="badge badge-medium">{adaptiveRiskLevel || "MEDIUM"}</span>
      </div>
      <p className="text-sm text-muted mb-3">Adaptive Risk Score: {Number(adaptiveScore || 0).toFixed(2)}%</p>
      <p className="text-sm font-medium mb-4">Decision: {decisionAction || "OTP"}</p>
      <div className="space-y-2">
        {riskDrivers.map((driver, index) => (
          <div key={`${driver.factor}-${index}`} className="flex items-center justify-between rounded-xl bg-slate-100/70 px-3 py-2">
            <span className="text-sm">{driver.factor}</span>
            <span className="text-sm font-semibold">+{(driver.impact * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
