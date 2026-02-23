import React, { useEffect, useMemo, useState } from "react";
import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  AreaChart,
  Area
} from "recharts";
import { getTransactions } from "../utils/fraudUtils";

const HEATMAP_PRESET_KEY = "securepay_heatmap_preset";

function normalizeRiskLevel(tx) {
  const label = (tx.riskLevel || "").toUpperCase();
  if (label.includes("CRITICAL")) return "CRITICAL";
  if (label.includes("HIGH")) return "HIGH";
  if (label.includes("MED")) return "MEDIUM";
  return "LOW";
}

function toRiskScore(tx) {
  return Number(tx.finalScore ?? tx.adaptiveScore ?? 20);
}

function buildGeoPoints(transactions) {
  return transactions.map((tx) => {
    const score = toRiskScore(tx);
    const lat = Number(tx.location?.lat ?? 20.5937);
    const lon = Number(tx.location?.lon ?? 78.9629);
    return {
      id: tx.id,
      lat,
      lon,
      amount: Number(tx.amount || 0),
      score,
      riskLevel: normalizeRiskLevel(tx)
    };
  });
}

function buildHourlyRisk(transactions) {
  const buckets = Array.from({ length: 24 }).map((_, hour) => ({
    hour,
    label: `${hour.toString().padStart(2, "0")}:00`,
    spikes: 0,
    avgScore: 0,
    totalAmount: 0,
    count: 0
  }));

  transactions.forEach((tx) => {
    const hour = new Date(tx.timestamp).getHours();
    const score = toRiskScore(tx);
    const bucket = buckets[hour];
    bucket.count += 1;
    bucket.totalAmount += Number(tx.amount || 0);
    bucket.avgScore += score;
    if (score > 70 || normalizeRiskLevel(tx) === "HIGH" || normalizeRiskLevel(tx) === "CRITICAL") {
      bucket.spikes += 1;
    }
  });

  return buckets.map((bucket) => ({
    ...bucket,
    avgScore: bucket.count ? Number((bucket.avgScore / bucket.count).toFixed(1)) : 0,
    totalAmount: Number(bucket.totalAmount.toFixed(1))
  }));
}

function buildDeviceRisk(transactions) {
  const map = new Map();
  transactions.forEach((tx) => {
    const deviceId = tx.deviceId || "Unknown";
    const existing = map.get(deviceId) || { deviceId, risk: 0, count: 0, totalAmount: 0 };
    existing.risk += toRiskScore(tx);
    existing.count += 1;
    existing.totalAmount += Number(tx.amount || 0);
    map.set(deviceId, existing);
  });
  return Array.from(map.values())
    .map((entry) => ({
      ...entry,
      risk: Number(entry.risk.toFixed(1)),
      avgRisk: Number((entry.risk / entry.count).toFixed(1)),
      totalAmount: Number(entry.totalAmount.toFixed(1))
    }))
    .sort((a, b) => b.risk - a.risk)
    .slice(0, 8);
}

function buildCorridorRisk(points) {
  const zoneMap = new Map();
  points.forEach((point) => {
    const latBand = Math.floor(point.lat / 5) * 5;
    const lonBand = Math.floor(point.lon / 5) * 5;
    const zone = `${latBand}/${lonBand}`;
    const existing = zoneMap.get(zone) || { zone, events: 0, risk: 0, maxScore: 0, totalAmount: 0 };
    existing.events += 1;
    existing.risk += point.score;
    existing.maxScore = Math.max(existing.maxScore, point.score);
    existing.totalAmount += point.amount;
    zoneMap.set(zone, existing);
  });

  return Array.from(zoneMap.values())
    .map((zone) => ({
      ...zone,
      avgRisk: Number((zone.risk / zone.events).toFixed(1)),
      totalAmount: Number(zone.totalAmount.toFixed(1))
    }))
    .sort((a, b) => b.avgRisk - a.avgRisk)
    .slice(0, 8);
}

function buildAuditHistory(transactions, highThreshold, criticalThreshold) {
  return transactions
    .slice()
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, 30)
    .map((tx, index) => {
      const score = toRiskScore(tx);
      const riskLevel = normalizeRiskLevel(tx);
      const action =
        score >= criticalThreshold
          ? "BLOCK_AND_REVIEW"
          : score >= Math.max(40, highThreshold - 5)
            ? "STEP_UP_VERIFICATION"
            : "ALLOW_WITH_MONITORING";
      const reasons = [];
      if (score >= highThreshold) reasons.push("High model risk score");
      if ((tx.amount || 0) > 5000) reasons.push("Elevated transaction amount");
      if (!tx.deviceId) reasons.push("Missing stable device signal");
      if (reasons.length === 0) reasons.push("Routine monitoring threshold");
      return {
        seq: index + 1,
        id: tx.id,
        userId: tx.userId || "Unknown",
        receiverId: tx.receiverId || "Unknown",
        timestamp: tx.timestamp,
        amount: Number(tx.amount || 0),
        score,
        riskLevel,
        action,
        reasons: reasons.join(" | "),
        deviceId: tx.deviceId || "Unknown",
        merchant: tx.merchant || "Unknown",
        channel: tx.channel || "Unknown",
        ip: tx.ip || "Unknown",
        locationLabel: tx.location?.city || "Unknown",
        rawFeatures: tx.features || {}
      };
    });
}

function riskColor(score, highThreshold, criticalThreshold) {
  if (score >= criticalThreshold) return "#dc2626";
  if (score >= highThreshold) return "#f59e0b";
  return "#0ea5e9";
}

function buildAnomalyStreaks(transactions, highThreshold) {
  const ordered = transactions
    .slice()
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  let currentHighStreak = 0;
  let maxHighStreak = 0;
  let currentRecoveryStreak = 0;
  let maxRecoveryStreak = 0;
  let latestHighTimestamp = "";

  ordered.forEach((tx) => {
    const score = toRiskScore(tx);
    if (score >= highThreshold) {
      currentHighStreak += 1;
      maxHighStreak = Math.max(maxHighStreak, currentHighStreak);
      currentRecoveryStreak = 0;
      latestHighTimestamp = tx.timestamp;
    } else {
      currentRecoveryStreak += 1;
      maxRecoveryStreak = Math.max(maxRecoveryStreak, currentRecoveryStreak);
      currentHighStreak = 0;
    }
  });

  return {
    currentHighStreak,
    maxHighStreak,
    currentRecoveryStreak,
    maxRecoveryStreak,
    latestHighTimestamp
  };
}

export default function FraudHeatmap() {
  const [transactions, setTransactions] = useState(() => getTransactions());
  const [riskFilter, setRiskFilter] = useState("ALL");
  const [timeFilter, setTimeFilter] = useState("ALL");
  const [auditSearch, setAuditSearch] = useState("");
  const [auditPage, setAuditPage] = useState(1);
  const [auditPageSize, setAuditPageSize] = useState(10);
  const [highThreshold, setHighThreshold] = useState(70);
  const [criticalThreshold, setCriticalThreshold] = useState(85);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(false);
  const [autoRefreshMs, setAutoRefreshMs] = useState(30000);
  const [expandedAuditKey, setExpandedAuditKey] = useState("");
  const [savedPreset, setSavedPreset] = useState(() => {
    try {
      const raw = localStorage.getItem(HEATMAP_PRESET_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    const refresh = () => setTransactions(getTransactions());
    window.addEventListener("transactions-updated", refresh);
    return () => window.removeEventListener("transactions-updated", refresh);
  }, []);

  useEffect(() => {
    if (!autoRefreshEnabled) return undefined;
    const timer = setInterval(() => {
      setTransactions(getTransactions());
    }, autoRefreshMs);
    return () => clearInterval(timer);
  }, [autoRefreshEnabled, autoRefreshMs]);

  const filteredTransactions = useMemo(() => {
    let next = transactions.slice();
    const now = Date.now();

    if (timeFilter === "24H") {
      next = next.filter((tx) => now - new Date(tx.timestamp).getTime() <= 24 * 60 * 60 * 1000);
    } else if (timeFilter === "7D") {
      next = next.filter((tx) => now - new Date(tx.timestamp).getTime() <= 7 * 24 * 60 * 60 * 1000);
    }

    if (riskFilter === "HIGH_PLUS") {
      next = next.filter((tx) => toRiskScore(tx) >= highThreshold);
    } else if (riskFilter === "CRITICAL_ONLY") {
      next = next.filter((tx) => toRiskScore(tx) >= criticalThreshold);
    }

    return next;
  }, [transactions, riskFilter, timeFilter, highThreshold, criticalThreshold]);

  const geoPoints = useMemo(() => buildGeoPoints(filteredTransactions), [filteredTransactions]);
  const hourlyRisk = useMemo(() => buildHourlyRisk(filteredTransactions), [filteredTransactions]);
  const deviceRisk = useMemo(() => buildDeviceRisk(filteredTransactions), [filteredTransactions]);
  const corridorRisk = useMemo(() => buildCorridorRisk(geoPoints), [geoPoints]);
  const auditHistory = useMemo(() => {
    const rows = buildAuditHistory(filteredTransactions, highThreshold, criticalThreshold);
    const q = auditSearch.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((row) =>
      [row.id, row.userId, row.receiverId, row.riskLevel, row.action, row.reasons]
        .join(" ")
        .toLowerCase()
        .includes(q)
    );
  }, [filteredTransactions, auditSearch, highThreshold, criticalThreshold]);

  const auditTotalPages = useMemo(
    () => Math.max(1, Math.ceil(auditHistory.length / auditPageSize)),
    [auditHistory.length, auditPageSize]
  );

  const pagedAuditHistory = useMemo(() => {
    const safePage = Math.min(auditPage, auditTotalPages);
    const start = (safePage - 1) * auditPageSize;
    return auditHistory.slice(start, start + auditPageSize);
  }, [auditHistory, auditPage, auditPageSize, auditTotalPages]);

  const metrics = useMemo(() => {
    const total = filteredTransactions.length;
    const high = filteredTransactions.filter((tx) => toRiskScore(tx) >= highThreshold).length;
    const critical = filteredTransactions.filter((tx) => toRiskScore(tx) >= criticalThreshold).length;
    const avg = total ? filteredTransactions.reduce((acc, tx) => acc + toRiskScore(tx), 0) / total : 0;
    return {
      total,
      high,
      critical,
      avg: Number(avg.toFixed(1))
    };
  }, [filteredTransactions, highThreshold, criticalThreshold]);

  const streaks = useMemo(
    () => buildAnomalyStreaks(filteredTransactions, highThreshold),
    [filteredTransactions, highThreshold]
  );

  useEffect(() => {
    setAuditPage(1);
  }, [riskFilter, timeFilter, auditSearch, auditPageSize]);

  useEffect(() => {
    if (auditPage > auditTotalPages) {
      setAuditPage(auditTotalPages);
    }
  }, [auditPage, auditTotalPages]);

  const downloadAuditCsv = () => {
    if (!auditHistory.length) return;
    const headers = ["seq", "transactionId", "userId", "receiverId", "timestamp", "amount", "score", "riskLevel", "action", "reasons"];
    const rows = auditHistory.map((row) => [
      row.seq,
      row.id,
      row.userId,
      row.receiverId,
      row.timestamp,
      row.amount,
      row.score,
      row.riskLevel,
      row.action,
      row.reasons
    ]);
    const csv = [headers.join(","), ...rows.map((cols) => cols.map((val) => `"${String(val).replace(/"/g, '""')}"`).join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "securepay-fraud-audit-history.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const saveCurrentPreset = () => {
    const preset = {
      riskFilter,
      timeFilter,
      highThreshold,
      criticalThreshold,
      auditSearch
    };
    localStorage.setItem(HEATMAP_PRESET_KEY, JSON.stringify(preset));
    setSavedPreset(preset);
  };

  const applySavedPreset = () => {
    if (!savedPreset) return;
    setRiskFilter(savedPreset.riskFilter || "ALL");
    setTimeFilter(savedPreset.timeFilter || "ALL");
    setHighThreshold(Number(savedPreset.highThreshold || 70));
    setCriticalThreshold(Number(savedPreset.criticalThreshold || 85));
    setAuditSearch(savedPreset.auditSearch || "");
  };

  const resetControls = () => {
    setRiskFilter("ALL");
    setTimeFilter("ALL");
    setAuditSearch("");
    setHighThreshold(70);
    setCriticalThreshold(85);
    setAutoRefreshEnabled(false);
    setAutoRefreshMs(30000);
    setExpandedAuditKey("");
  };

  return (
    <div className="space-y-6">
      <div className="card p-5">
        <div className="grid gap-3 md:grid-cols-6">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted mb-2">Risk Filter</p>
            <select
              className="w-full border rounded-xl px-3 py-2"
              value={riskFilter}
              onChange={(event) => setRiskFilter(event.target.value)}
            >
              <option value="ALL">All Risks</option>
              <option value="HIGH_PLUS">High and Above</option>
              <option value="CRITICAL_ONLY">Critical Only</option>
            </select>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted mb-2">Time Window</p>
            <select
              className="w-full border rounded-xl px-3 py-2"
              value={timeFilter}
              onChange={(event) => setTimeFilter(event.target.value)}
            >
              <option value="ALL">All Time</option>
              <option value="24H">Last 24 Hours</option>
              <option value="7D">Last 7 Days</option>
            </select>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted mb-2">Auto Refresh</p>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={autoRefreshEnabled}
                onChange={(event) => setAutoRefreshEnabled(event.target.checked)}
              />
              <span>{autoRefreshEnabled ? "Enabled" : "Disabled"}</span>
            </label>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted mb-2">Refresh Rate</p>
            <select
              className="w-full border rounded-xl px-3 py-2"
              value={autoRefreshMs}
              onChange={(event) => setAutoRefreshMs(Number(event.target.value))}
              disabled={!autoRefreshEnabled}
            >
              <option value={15000}>15 sec</option>
              <option value={30000}>30 sec</option>
              <option value={60000}>60 sec</option>
            </select>
          </div>
          <div className="md:col-span-2">
            <p className="text-xs uppercase tracking-wide text-muted mb-2">Audit Search</p>
            <input
              className="w-full border rounded-xl px-3 py-2"
              value={auditSearch}
              onChange={(event) => setAuditSearch(event.target.value)}
              placeholder="Search by transaction, user, action, risk, or reason"
            />
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-2 mt-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted mb-2">High Risk Threshold: {highThreshold}</p>
            <input
              type="range"
              min={40}
              max={90}
              value={highThreshold}
              className="w-full"
              onChange={(event) => {
                const value = Number(event.target.value);
                setHighThreshold(value);
                if (criticalThreshold <= value) setCriticalThreshold(Math.min(99, value + 1));
              }}
            />
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted mb-2">Critical Threshold: {criticalThreshold}</p>
            <input
              type="range"
              min={50}
              max={99}
              value={criticalThreshold}
              className="w-full"
              onChange={(event) => {
                const value = Number(event.target.value);
                setCriticalThreshold(Math.max(value, highThreshold + 1));
              }}
            />
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 mt-3">
          <button className="btn-outline" type="button" onClick={saveCurrentPreset}>
            Save Preset
          </button>
          <button className="btn-outline" type="button" onClick={applySavedPreset} disabled={!savedPreset}>
            Apply Saved Preset
          </button>
          <button className="btn-outline" type="button" onClick={resetControls}>
            Reset Controls
          </button>
          <button
            className="btn-outline"
            type="button"
            onClick={() => {
              setRiskFilter("CRITICAL_ONLY");
              setTimeFilter("24H");
              setAuditSearch("");
            }}
          >
            Quick Preset: Critical 24H
          </button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-4">
        <div className="card p-5">
          <p className="text-xs uppercase tracking-wide text-muted">Total Events</p>
          <h3 className="text-2xl font-semibold mt-2">{metrics.total}</h3>
        </div>
        <div className="card p-5">
          <p className="text-xs uppercase tracking-wide text-muted">High Risk</p>
          <h3 className="text-2xl font-semibold mt-2 text-amber-600">{metrics.high}</h3>
        </div>
        <div className="card p-5">
          <p className="text-xs uppercase tracking-wide text-muted">Critical Alerts</p>
          <h3 className="text-2xl font-semibold mt-2 text-red-600">{metrics.critical}</h3>
        </div>
        <div className="card p-5">
          <p className="text-xs uppercase tracking-wide text-muted">Average Risk Score</p>
          <h3 className="text-2xl font-semibold mt-2 text-sky-600">{metrics.avg}</h3>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-4">
        <div className="card p-5">
          <p className="text-xs uppercase tracking-wide text-muted">Current High-Risk Streak</p>
          <h3 className="text-2xl font-semibold mt-2 text-amber-600">{streaks.currentHighStreak}</h3>
        </div>
        <div className="card p-5">
          <p className="text-xs uppercase tracking-wide text-muted">Max High-Risk Streak</p>
          <h3 className="text-2xl font-semibold mt-2 text-red-600">{streaks.maxHighStreak}</h3>
        </div>
        <div className="card p-5">
          <p className="text-xs uppercase tracking-wide text-muted">Current Recovery Streak</p>
          <h3 className="text-2xl font-semibold mt-2 text-emerald-600">{streaks.currentRecoveryStreak}</h3>
        </div>
        <div className="card p-5">
          <p className="text-xs uppercase tracking-wide text-muted">Latest High Alert</p>
          <p className="text-sm mt-2 text-muted">
            {streaks.latestHighTimestamp ? new Date(streaks.latestHighTimestamp).toLocaleString() : "No high-risk event"}
          </p>
        </div>
      </div>

      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-2">Advanced Fraud Geo Heatmap</h2>
        <p className="text-sm text-muted mb-4">
          Multi-intensity geospatial scatter with risk-graded hotspots, amount-aware radius scaling, and corridor concentration visibility.
        </p>
        <div className="h-[380px] rounded-xl overflow-hidden border border-slate-200 bg-slate-50 p-4">
          <svg width="100%" height="100%" viewBox="0 0 900 360">
            <defs>
              <linearGradient id="bg-grid" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#e2e8f0" />
                <stop offset="100%" stopColor="#cbd5e1" />
              </linearGradient>
            </defs>
            <rect x="0" y="0" width="900" height="360" rx="12" fill="url(#bg-grid)" />
            {geoPoints.map((point) => {
              const x = ((point.lon + 180) / 360) * 900;
              const y = ((90 - point.lat) / 180) * 360;
              const radius = Math.max(5, Math.min(22, point.score / 7 + point.amount / 4000));
              const color = riskColor(point.score, highThreshold, criticalThreshold);
              return (
                <g key={point.id}>
                  <circle cx={x} cy={y} r={radius} fill={color} fillOpacity="0.2" />
                  <circle cx={x} cy={y} r={Math.max(2, radius / 3)} fill={color} fillOpacity="0.65" />
                </g>
              );
            })}
            <text x="14" y="22" fill="#334155" fontSize="12">Risk intensity and amount-weighted fraud activity map</text>
          </svg>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-3">Hourly Risk and Spike Dynamics</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={hourlyRisk}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" hide />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="spikes" stroke="#dc2626" strokeWidth={2} name="Risk Spikes" />
                <Line type="monotone" dataKey="avgScore" stroke="#0284c7" strokeWidth={2} name="Average Score" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-3">Transaction Volume Exposure by Hour</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={hourlyRisk}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" hide />
                <YAxis />
                <Tooltip />
                <Area type="monotone" dataKey="totalAmount" stroke="#0891b2" fill="#67e8f9" name="Amount" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-3">Top Risky Devices</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={deviceRisk}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="deviceId" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="risk" fill="#0ea5e9" radius={[6, 6, 0, 0]} name="Cumulative Risk" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-3">High-Risk Geo Corridors</h3>
          <div className="overflow-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-muted border-b border-slate-200">
                  <th className="py-2 pr-3">Zone</th>
                  <th className="py-2 pr-3">Events</th>
                  <th className="py-2 pr-3">Avg Risk</th>
                  <th className="py-2 pr-3">Max Score</th>
                  <th className="py-2 pr-3">Amount</th>
                </tr>
              </thead>
              <tbody>
                {corridorRisk.map((zone) => (
                  <tr key={zone.zone} className="border-b border-slate-100">
                    <td className="py-2 pr-3 font-medium">{zone.zone}</td>
                    <td className="py-2 pr-3">{zone.events}</td>
                    <td className="py-2 pr-3">{zone.avgRisk}</td>
                    <td className="py-2 pr-3">{zone.maxScore}</td>
                    <td className="py-2 pr-3">INR {zone.totalAmount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="card p-6">
        <div className="flex items-center justify-between gap-3 mb-3">
          <h3 className="text-lg font-semibold">Fraud Audit Log History</h3>
          <button className="btn-outline" type="button" onClick={downloadAuditCsv}>
            Export Audit CSV
          </button>
        </div>
        <p className="text-sm text-muted mb-4">
          Chronological decision history for recent transactions with inferred risk actions and traceable reasoning markers for analyst review.
        </p>
        <div className="overflow-auto">
          <table className="min-w-full text-xs">
            <thead>
              <tr className="text-left text-muted border-b border-slate-200">
                <th className="py-2 pr-3">#</th>
                <th className="py-2 pr-3">Transaction</th>
                <th className="py-2 pr-3">User</th>
                <th className="py-2 pr-3">Receiver</th>
                <th className="py-2 pr-3">Timestamp</th>
                <th className="py-2 pr-3">Amount</th>
                <th className="py-2 pr-3">Score</th>
                <th className="py-2 pr-3">Risk</th>
                <th className="py-2 pr-3">Action</th>
                <th className="py-2 pr-3">Reason Trace</th>
                <th className="py-2 pr-3">Details</th>
              </tr>
            </thead>
            <tbody>
              {pagedAuditHistory.map((row) => (
                <React.Fragment key={`${row.id}-${row.seq}`}>
                  <tr className="border-b border-slate-100">
                    <td className="py-2 pr-3">{row.seq}</td>
                    <td className="py-2 pr-3 font-medium">{row.id}</td>
                    <td className="py-2 pr-3">{row.userId}</td>
                    <td className="py-2 pr-3">{row.receiverId}</td>
                    <td className="py-2 pr-3 whitespace-nowrap">{new Date(row.timestamp).toLocaleString()}</td>
                    <td className="py-2 pr-3">INR {row.amount}</td>
                    <td className="py-2 pr-3">{row.score}</td>
                    <td className="py-2 pr-3">{row.riskLevel}</td>
                    <td className="py-2 pr-3">{row.action}</td>
                    <td className="py-2 pr-3">{row.reasons}</td>
                    <td className="py-2 pr-3">
                      <button
                        className="btn-outline"
                        type="button"
                        onClick={() =>
                          setExpandedAuditKey((current) => (current === `${row.id}-${row.seq}` ? "" : `${row.id}-${row.seq}`))
                        }
                      >
                        {expandedAuditKey === `${row.id}-${row.seq}` ? "Hide" : "View"}
                      </button>
                    </td>
                  </tr>
                  {expandedAuditKey === `${row.id}-${row.seq}` && (
                    <tr className="bg-slate-50 border-b border-slate-100">
                      <td className="py-2 pr-3" colSpan={11}>
                        <div className="grid gap-2 md:grid-cols-3 text-xs">
                          <p><b>Device:</b> {row.deviceId}</p>
                          <p><b>Merchant:</b> {row.merchant}</p>
                          <p><b>Channel:</b> {row.channel}</p>
                          <p><b>IP:</b> {row.ip}</p>
                          <p><b>Location:</b> {row.locationLabel}</p>
                          <p><b>Feature Keys:</b> {Object.keys(row.rawFeatures).length}</p>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-muted">
            Showing {(auditPage - 1) * auditPageSize + (pagedAuditHistory.length ? 1 : 0)}-
            {(auditPage - 1) * auditPageSize + pagedAuditHistory.length} of {auditHistory.length}
          </p>
          <div className="flex items-center gap-2">
            <select
              className="border rounded-lg px-2 py-1 text-xs"
              value={auditPageSize}
              onChange={(event) => setAuditPageSize(Number(event.target.value))}
            >
              <option value={10}>10 / page</option>
              <option value={20}>20 / page</option>
              <option value={30}>30 / page</option>
            </select>
            <button
              className="btn-outline"
              type="button"
              disabled={auditPage <= 1}
              onClick={() => setAuditPage((page) => Math.max(1, page - 1))}
            >
              Previous
            </button>
            <span className="text-xs text-muted px-1">
              Page {auditPage} / {auditTotalPages}
            </span>
            <button
              className="btn-outline"
              type="button"
              disabled={auditPage >= auditTotalPages}
              onClick={() => setAuditPage((page) => Math.min(auditTotalPages, page + 1))}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
