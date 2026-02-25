import React from "react";

export default function FilterPanel({ filters, onChange, onApply, onReset, loading }) {
  return (
    <section className="hmi-panel">
      <h2 className="hmi-title">Heatmap Filters</h2>
      <p className="hmi-subtitle">Date, risk, amount, user segment, and device filters.</p>

      <div className="hmi-grid-2" style={{ marginTop: "0.8rem" }}>
        <label>
          <span className="hmi-subtitle">Start Date</span>
          <input
            className="hmi-input"
            type="date"
            value={filters.start_date}
            onChange={(e) => onChange("start_date", e.target.value)}
          />
        </label>
        <label>
          <span className="hmi-subtitle">End Date</span>
          <input
            className="hmi-input"
            type="date"
            value={filters.end_date}
            onChange={(e) => onChange("end_date", e.target.value)}
          />
        </label>
      </div>

      <div style={{ marginTop: "0.75rem" }}>
        <label>
          <span className="hmi-subtitle">Risk Level</span>
          <select className="hmi-select" value={filters.risk_level} onChange={(e) => onChange("risk_level", e.target.value)}>
            <option value="">All</option>
            <option value="Low">Low</option>
            <option value="Medium">Medium</option>
            <option value="High">High</option>
            <option value="Critical">Critical</option>
          </select>
        </label>
      </div>

      <div className="hmi-grid-2" style={{ marginTop: "0.75rem" }}>
        <label>
          <span className="hmi-subtitle">Min Amount</span>
          <input
            className="hmi-input"
            type="number"
            min="0"
            placeholder="0"
            value={filters.min_amount}
            onChange={(e) => onChange("min_amount", e.target.value)}
          />
        </label>
        <label>
          <span className="hmi-subtitle">Max Amount</span>
          <input
            className="hmi-input"
            type="number"
            min="0"
            placeholder="100000"
            value={filters.max_amount}
            onChange={(e) => onChange("max_amount", e.target.value)}
          />
        </label>
      </div>

      <div style={{ marginTop: "0.75rem" }}>
        <label>
          <span className="hmi-subtitle">User Segment (User ID)</span>
          <input
            className="hmi-input"
            type="text"
            value={filters.user_segment}
            onChange={(e) => onChange("user_segment", e.target.value)}
            placeholder="optional user id"
          />
        </label>
      </div>

      <div style={{ marginTop: "0.75rem" }}>
        <label>
          <span className="hmi-subtitle">Device Type</span>
          <select className="hmi-select" value={filters.device_type} onChange={(e) => onChange("device_type", e.target.value)}>
            <option value="">All</option>
            <option value="Android">Android</option>
            <option value="iOS">iOS</option>
            <option value="Windows">Windows</option>
            <option value="macOS">macOS</option>
            <option value="Web">Web</option>
            <option value="Unknown">Unknown</option>
          </select>
        </label>
      </div>

      <div style={{ marginTop: "0.75rem" }}>
        <label>
          <span className="hmi-subtitle">Limit</span>
          <input
            className="hmi-input"
            type="number"
            min="50"
            max="10000"
            step="50"
            value={filters.limit}
            onChange={(e) => onChange("limit", Number(e.target.value || 2000))}
          />
        </label>
      </div>

      <div style={{ display: "flex", gap: "0.6rem", marginTop: "1rem" }}>
        <button className="btn-primary" onClick={onApply} disabled={loading}>
          {loading ? "Loading..." : "Apply Filters"}
        </button>
        <button className="btn-outline" onClick={onReset} disabled={loading}>
          Reset
        </button>
      </div>
    </section>
  );
}

