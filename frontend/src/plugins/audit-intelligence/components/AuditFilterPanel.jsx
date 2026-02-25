import React from "react";

const RISK_OPTIONS = ["", "Low", "Medium", "High", "Critical"];
const STATUS_OPTIONS = ["", "SUCCESS", "PENDING", "FAILED", "DECLINED"];

export default function AuditFilterPanel({ filters, onChange, onApply, onReset, loading }) {
  return (
    <section className="card ai-plugin-card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold">Audit Filters</h3>
        <span className="ai-plugin-subtle">From - To</span>
      </div>

      <div className="ai-plugin-toolbar">
        <label>
          <span className="ai-plugin-subtle">Start Date</span>
          <input
            className="ai-plugin-input"
            type="date"
            value={filters.start_date || ""}
            onChange={(event) => onChange("start_date", event.target.value)}
          />
        </label>

        <label>
          <span className="ai-plugin-subtle">End Date</span>
          <input
            className="ai-plugin-input"
            type="date"
            value={filters.end_date || ""}
            onChange={(event) => onChange("end_date", event.target.value)}
          />
        </label>

        <label>
          <span className="ai-plugin-subtle">Risk Level</span>
          <select
            className="ai-plugin-select"
            value={filters.risk_level || ""}
            onChange={(event) => onChange("risk_level", event.target.value)}
          >
            {RISK_OPTIONS.map((option) => (
              <option key={option || "all"} value={option}>
                {option || "All Risk Levels"}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span className="ai-plugin-subtle">Transaction Status</span>
          <select
            className="ai-plugin-select"
            value={filters.transaction_status || ""}
            onChange={(event) => onChange("transaction_status", event.target.value)}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option || "all"} value={option}>
                {option || "All Statuses"}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span className="ai-plugin-subtle">User ID</span>
          <input
            className="ai-plugin-input"
            placeholder="Filter by user"
            value={filters.user_id || ""}
            onChange={(event) => onChange("user_id", event.target.value)}
          />
        </label>
      </div>

      <div className="flex gap-2 mt-4">
        <button className="btn-primary" type="button" onClick={onApply} disabled={loading}>
          {loading ? "Refreshing..." : "Apply Filters"}
        </button>
        <button className="btn-outline" type="button" onClick={onReset} disabled={loading}>
          Reset
        </button>
      </div>
    </section>
  );
}
