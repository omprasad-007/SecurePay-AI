import { getTransactions } from "../../../utils/fraudUtils";

const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function clamp(value, min = 0, max = 1) {
  return Math.max(min, Math.min(max, Number(value) || 0));
}

function num(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function riskLevel(score) {
  if (score <= 30) return "Low";
  if (score <= 60) return "Medium";
  if (score <= 80) return "High";
  return "Critical";
}

function deviceType(deviceId) {
  const text = String(deviceId || "").toLowerCase();
  if (text.includes("android")) return "Android";
  if (text.includes("iphone") || text.includes("ios")) return "iOS";
  if (text.includes("windows")) return "Windows";
  if (text.includes("mac")) return "macOS";
  if (text.includes("web")) return "Web";
  return "Unknown";
}

function normalize(tx, index = 0) {
  const timestamp = new Date(tx.timestamp || Date.now() - index * 3600 * 1000);
  const score = num(tx.finalScore ?? tx.overallRiskScore ?? 0);
  const location = tx.location || {};
  return {
    transaction_id: String(tx.id || `TXN_${index + 1}`),
    user_id: String(tx.userId || "unknown"),
    merchant_name: String(tx.merchant || "Unknown"),
    transaction_amount: num(tx.amount, 0),
    risk_score: score,
    risk_level: riskLevel(score),
    risk_reasons: Array.isArray(tx.riskDrivers) ? tx.riskDrivers : [],
    transaction_datetime: timestamp,
    city: String(location.city || "Unknown"),
    state: String(location.state || ""),
    country: String(location.country || "India"),
    geo_latitude: location.lat == null ? null : num(location.lat, null),
    geo_longitude: location.lon == null ? null : num(location.lon, null),
    device_id: String(tx.deviceId || "unknown-device"),
    ip_address: String(tx.ip || "0.0.0.0"),
  };
}

function applyFilters(rows, params = {}) {
  const now = new Date();
  const startDate = params.start_date ? new Date(params.start_date) : new Date(now.getTime() - 30 * 24 * 3600 * 1000);
  const endDate = params.end_date ? new Date(params.end_date) : now;
  endDate.setHours(23, 59, 59, 999);
  const minAmount = params.min_amount == null ? null : num(params.min_amount, 0);
  const maxAmount = params.max_amount == null ? null : num(params.max_amount, Number.MAX_SAFE_INTEGER);
  const risk = String(params.risk_level || "").toLowerCase();
  const userSegment = String(params.user_segment || "");
  const device = String(params.device_type || "").toLowerCase();
  const limit = Math.max(1, num(params.limit, 2000));

  return rows
    .filter((row) => row.transaction_datetime >= startDate && row.transaction_datetime <= endDate)
    .filter((row) => !risk || row.risk_level.toLowerCase() === risk)
    .filter((row) => minAmount == null || row.transaction_amount >= minAmount)
    .filter((row) => maxAmount == null || row.transaction_amount <= maxAmount)
    .filter((row) => !userSegment || row.user_id === userSegment)
    .filter((row) => !device || deviceType(row.device_id).toLowerCase() === device)
    .sort((a, b) => b.transaction_datetime - a.transaction_datetime)
    .slice(0, limit);
}

function geographic(rows) {
  const map = new Map();
  rows.forEach((row) => {
    if (row.geo_latitude == null || row.geo_longitude == null) return;
    const lat = Number(row.geo_latitude.toFixed(3));
    const lng = Number(row.geo_longitude.toFixed(3));
    const key = `${lat},${lng}`;
    if (!map.has(key)) map.set(key, { lat, lng, count: 0, high: 0, riskSum: 0 });
    const bucket = map.get(key);
    bucket.count += 1;
    bucket.riskSum += row.risk_score;
    if (row.risk_score > 60) bucket.high += 1;
  });
  const points = Array.from(map.values()).map((bucket) => {
    const avg = bucket.count ? bucket.riskSum / bucket.count : 0;
    const density = clamp((avg / 100) * (bucket.high / Math.max(1, bucket.count)));
    return {
      lat: bucket.lat,
      lng: bucket.lng,
      risk_density: Number(density.toFixed(4)),
      fraud_count: bucket.high,
      avg_risk_score: Number(avg.toFixed(2)),
      heat_intensity: Number(clamp(density * Math.log(2 + bucket.high), 0, 3).toFixed(4)),
      risk_level: riskLevel(avg),
    };
  });
  points.sort((a, b) => b.heat_intensity - a.heat_intensity);
  return {
    points,
    meta: {
      total_points: points.length,
      total_transactions: rows.length,
      high_risk_transactions: rows.filter((row) => row.risk_score > 60).length,
    },
  };
}

function timePattern(rows) {
  const buckets = {};
  for (let d = 0; d < 7; d += 1) for (let h = 0; h < 24; h += 1) buckets[`${d}-${h}`] = { c: 0, h: 0, r: 0 };
  rows.forEach((row) => {
    const jsDay = row.transaction_datetime.getDay();
    const day = jsDay === 0 ? 6 : jsDay - 1;
    const hour = row.transaction_datetime.getHours();
    const bucket = buckets[`${day}-${hour}`];
    bucket.c += 1;
    bucket.r += row.risk_score;
    if (row.risk_score > 60) bucket.h += 1;
  });
  const matrix = [];
  for (let d = 0; d < 7; d += 1) {
    for (let h = 0; h < 24; h += 1) {
      const bucket = buckets[`${d}-${h}`];
      const count = Math.max(1, bucket.c);
      const avg = bucket.r / count;
      const intensity = clamp((bucket.h / count) * 0.6 + (avg / 100) * 0.4);
      matrix.push({
        day_index: d,
        day_name: DAY_NAMES[d],
        hour: h,
        fraud_intensity: Number(intensity.toFixed(4)),
        fraud_count: bucket.h,
        avg_risk_score: Number(avg.toFixed(2)),
      });
    }
  }
  return { matrix, meta: { total_transactions: rows.length } };
}

function deviceAnomaly(rows) {
  const byDevice = {};
  const byIp = {};
  rows.forEach((row) => {
    if (!byDevice[row.device_id]) byDevice[row.device_id] = [];
    byDevice[row.device_id].push(row);
    if (!byIp[row.ip_address]) byIp[row.ip_address] = new Set();
    byIp[row.ip_address].add(row.device_id);
  });
  const devices = Object.entries(byDevice).map(([deviceId, items], index) => {
    const score = items.reduce((sum, row) => sum + row.risk_score, 0) / Math.max(1, items.length);
    const ipSet = new Set(items.map((item) => item.ip_address));
    const geoSet = new Set(items.map((item) => item.city));
    const ipRisk = clamp(ipSet.size / Math.max(1, items.length), 0, 1);
    const geoRisk = clamp((geoSet.size - 1) / 5, 0, 1);
    let sharedIp = 0;
    ipSet.forEach((ip) => {
      sharedIp = Math.max(sharedIp, clamp(((byIp[ip]?.size || 1) - 1) / 6, 0, 1));
    });
    const anomaly = (0.35 * (score / 100)) + (0.30 * geoRisk) + (0.20 * sharedIp) + (0.15 * ipRisk);
    const anomalyPct = Number((anomaly * 100).toFixed(2));
    return {
      device_id: deviceId,
      device_type: deviceType(deviceId),
      transaction_count: items.length,
      login_frequency: Number((items.length / 2).toFixed(2)),
      transaction_speed: Number((items.length / 3).toFixed(2)),
      geo_mismatch_score: Number((geoRisk * 100).toFixed(2)),
      ip_anomaly_score: Number((ipRisk * 100).toFixed(2)),
      anomaly_score: anomalyPct,
      cluster_label: `C${index % 4}`,
      anomaly_level: riskLevel(anomalyPct),
    };
  });
  devices.sort((a, b) => b.anomaly_score - a.anomaly_score);
  return { devices, meta: { device_count: devices.length, critical_devices: devices.filter((d) => d.anomaly_level === "Critical").length } };
}

function fraudClusters(rows) {
  const userMerchants = {};
  rows.forEach((row) => {
    if (!userMerchants[row.user_id]) userMerchants[row.user_id] = new Set();
    userMerchants[row.user_id].add(row.merchant_name);
  });
  const users = Object.keys(userMerchants);
  const clusters = [];
  for (let i = 0; i < users.length; i += 1) {
    for (let j = i + 1; j < users.length; j += 1) {
      const u1 = users[i];
      const u2 = users[j];
      const shared = Array.from(userMerchants[u1]).filter((merchant) => userMerchants[u2].has(merchant));
      if (!shared.length) continue;
      const clusterRows = rows.filter((row) => row.user_id === u1 || row.user_id === u2);
      const avgRisk = clusterRows.reduce((sum, row) => sum + row.risk_score, 0) / Math.max(1, clusterRows.length);
      const ringRisk = clamp((shared.length / 5) * 30 + (avgRisk / 100) * 70, 0, 100);
      clusters.push({
        cluster_id: `cluster-${clusters.length + 1}`,
        cluster_size: 2,
        users: [u1, u2],
        shared_devices: [],
        shared_ips: [],
        shared_accounts: shared,
        high_risk_ratio: Number(((clusterRows.filter((r) => r.risk_score > 60).length / Math.max(1, clusterRows.length)) * 100).toFixed(2)),
        ring_risk_score: Number(ringRisk.toFixed(2)),
        summary: `Coordinated merchant pattern between ${u1} and ${u2}`,
        detected_at: new Date().toISOString(),
      });
    }
  }
  clusters.sort((a, b) => b.ring_risk_score - a.ring_risk_score);
  return { clusters: clusters.slice(0, 50), meta: { cluster_count: clusters.length, high_severity_clusters: clusters.filter((c) => c.ring_risk_score > 70).length } };
}

function predictiveRisk(rows) {
  const ordered = [...rows].sort((a, b) => a.transaction_datetime - b.transaction_datetime);
  const mid = Math.floor(ordered.length / 2);
  const prev = ordered.slice(0, mid || ordered.length);
  const curr = ordered.slice(mid || 0);
  const byCity = {};
  const apply = (arr, key) => arr.forEach((row) => {
    const city = row.city || "Unknown";
    if (!byCity[city]) byCity[city] = { city, prev: { t: 0, h: 0 }, curr: { t: 0, h: 0 }, geo: { lat: row.geo_latitude, lng: row.geo_longitude }, state: row.state, country: row.country };
    byCity[city][key].t += 1;
    if (row.risk_score > 60) byCity[city][key].h += 1;
  });
  apply(prev, "prev");
  apply(curr, "curr");
  const zones = Object.values(byCity).map((city) => {
    const prevDensity = city.prev.h / Math.max(1, city.prev.t);
    const currDensity = city.curr.h / Math.max(1, city.curr.t);
    const growth = (currDensity - prevDensity) / Math.max(0.05, prevDensity || 0.05);
    const velocity = (city.curr.t - city.prev.t) / Math.max(1, city.prev.t || 1);
    const predicted = clamp((currDensity * 0.5) + (clamp(growth, -1, 2) * 0.3) + (clamp(velocity, -1, 3) * 0.2), 0, 1) * 100;
    return {
      city: city.city,
      state: city.state,
      country: city.country,
      geo_latitude: city.geo.lat,
      geo_longitude: city.geo.lng,
      historical_density: Number(prevDensity.toFixed(4)),
      growth_rate: Number(growth.toFixed(4)),
      transaction_growth_velocity: Number(velocity.toFixed(4)),
      predicted_risk_score: Number(predicted.toFixed(2)),
      label: growth > 0.25 || predicted > 70 ? "Predicted Risk Escalation" : "Monitor",
    };
  });
  zones.sort((a, b) => b.predicted_risk_score - a.predicted_risk_score);
  return { zones, meta: { zone_count: zones.length, escalation_count: zones.filter((z) => z.label === "Predicted Risk Escalation").length } };
}

function zoneDrilldown(rows, params = {}) {
  const lat = num(params.lat, 0);
  const lng = num(params.lng, 0);
  const radius = num(params.radius_degrees, 0.25);
  const zoneRows = rows.filter((row) => row.geo_latitude != null && row.geo_longitude != null)
    .filter((row) => Math.abs(row.geo_latitude - lat) <= radius && Math.abs(row.geo_longitude - lng) <= radius);
  const total = zoneRows.length;
  const high = zoneRows.filter((row) => row.risk_score > 60).length;
  return {
    total_transactions: total,
    fraud_percentage: Number(((high / Math.max(1, total)) * 100).toFixed(2)),
    top_users: Object.entries(zoneRows.reduce((acc, row) => ({ ...acc, [row.user_id]: (acc[row.user_id] || 0) + 1 }), {}))
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([user_id, transaction_count]) => ({ user_id, transaction_count })),
    top_devices: Object.entries(zoneRows.reduce((acc, row) => ({ ...acc, [row.device_id]: (acc[row.device_id] || 0) + 1 }), {}))
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([device_id, transaction_count]) => ({ device_id, device_type: deviceType(device_id), transaction_count })),
    risk_breakdown: {
      Low: zoneRows.filter((row) => row.risk_score <= 30).length,
      Medium: zoneRows.filter((row) => row.risk_score > 30 && row.risk_score <= 60).length,
      High: zoneRows.filter((row) => row.risk_score > 60 && row.risk_score <= 80).length,
      Critical: zoneRows.filter((row) => row.risk_score > 80).length,
    },
    ai_summary: total
      ? `Zone around (${lat.toFixed(3)}, ${lng.toFixed(3)}) has ${(high / Math.max(1, total) * 100).toFixed(1)}% high-risk activity.`
      : "No transactions found for this heat zone.",
  };
}

function summary(rows, params) {
  const timelineMap = {};
  rows.forEach((row) => {
    const key = row.transaction_datetime.toISOString().slice(0, 10);
    if (!timelineMap[key]) timelineMap[key] = { date: key, t: 0, h: 0, r: 0 };
    timelineMap[key].t += 1;
    timelineMap[key].r += row.risk_score;
    if (row.risk_score > 60) timelineMap[key].h += 1;
  });
  const timeline = Object.values(timelineMap).sort((a, b) => new Date(a.date) - new Date(b.date)).map((item) => ({
    date: item.date,
    transaction_volume: item.t,
    fraud_rate: Number(((item.h / Math.max(1, item.t)) * 100).toFixed(2)),
    avg_risk_score: Number((item.r / Math.max(1, item.t)).toFixed(2)),
  }));
  const avg = rows.length ? rows.reduce((sum, row) => sum + row.risk_score, 0) / rows.length : 0;
  const time = timePattern(rows);
  const peak = [...time.matrix].sort((a, b) => b.fraud_intensity - a.fraud_intensity)[0];
  const topWindow = peak ? `${peak.day_name} ${String(peak.hour).padStart(2, "0")}:00-${String((peak.hour + 1) % 24).padStart(2, "0")}:00` : "No peak";
  const cityCounter = rows.filter((row) => row.risk_score > 60).reduce((acc, row) => ({ ...acc, [row.city]: (acc[row.city] || 0) + 1 }), {});
  const topRegionEntry = Object.entries(cityCounter).sort((a, b) => b[1] - a[1])[0];
  const topRegion = topRegionEntry ? `${topRegionEntry[0]} (${topRegionEntry[1]} high-risk txns)` : "No dominant region";
  const clusters = fraudClusters(rows);
  const graph = {
    nodes: clusters.clusters.flatMap((cluster) => [{ id: `cluster:${cluster.cluster_id}`, type: "cluster", risk_score: cluster.ring_risk_score }, ...cluster.users.map((user) => ({ id: `user:${user}`, type: "user" }))]),
    edges: clusters.clusters.flatMap((cluster) => cluster.users.map((user) => ({ source: `cluster:${cluster.cluster_id}`, target: `user:${user}`, kind: "member" }))),
  };
  return {
    overall_risk_score: Number(avg.toFixed(2)),
    fraud_concentration_change_pct: 0,
    top_region: topRegion,
    top_time_window: topWindow,
    linked_device_pattern: "Local fallback pattern",
    ai_summary: `Fraud concentration analysis for ${params.start_date || "current period"} to ${params.end_date || "current period"} shows hotspot in ${topRegion}.`,
    timeline,
    layers: {
      velocity_risk_layer: [],
      amount_deviation_layer: [],
      cross_border_fraud_layer: [],
      risk_evolution_timeline: timeline,
      fraud_ring_visualization: graph,
    },
  };
}

function compliance(rows, threshold = 100000) {
  const clusters = fraudClusters(rows);
  const clusterByUser = {};
  clusters.clusters.forEach((cluster) => cluster.users.forEach((user) => { clusterByUser[user] = cluster.cluster_id; }));
  const tx = rows
    .filter((row) => row.risk_score > 80 || clusterByUser[row.user_id] || row.transaction_amount >= threshold)
    .map((row) => ({
      transaction_id: row.transaction_id,
      user_id: row.user_id,
      risk_score: Number(row.risk_score.toFixed(2)),
      risk_reasons: row.risk_reasons,
      city: row.city,
      country: row.country,
      device_id: row.device_id,
      cluster_id: clusterByUser[row.user_id] || null,
      compliance_status: row.risk_score > 90 || clusterByUser[row.user_id] ? "SAR_CANDIDATE" : "REVIEW_REQUIRED",
    }));
  const total = rows.length;
  const suspicious = tx.length;
  return {
    report_generated_at: new Date().toISOString(),
    total_transactions: total,
    suspicious_transactions: suspicious,
    fraud_rate: Number(((suspicious / Math.max(1, total)) * 100).toFixed(2)),
    top_suspicious_accounts: [],
    transactions: tx.slice(0, 1000),
    executive_summary: `Compliance scan processed ${total} transactions; ${suspicious} flagged.`,
  };
}

function suspicious(rows, threshold = 100000) {
  const base = compliance(rows, threshold);
  return {
    generated_at: new Date().toISOString(),
    total_flagged: base.transactions.length,
    transactions: base.transactions.map((item) => ({
      transaction_id: item.transaction_id,
      user_details: { user_id: item.user_id },
      risk_score: item.risk_score,
      risk_reasons: item.risk_reasons,
      geo_data: { city: item.city, country: item.country },
      device_fingerprint: item.device_id,
      ml_probability: Number((item.risk_score / 100).toFixed(4)),
      fraud_cluster_id: item.cluster_id,
      amount: rows.find((row) => row.transaction_id === item.transaction_id)?.transaction_amount || 0,
      timestamp: rows.find((row) => row.transaction_id === item.transaction_id)?.transaction_datetime?.toISOString() || new Date().toISOString(),
      anomaly_score: item.risk_score,
      rule_based_score: item.risk_score,
      final_risk_level: riskLevel(item.risk_score),
      feature_categories: { transaction: {}, behavioral: {}, network: {} },
    })),
  };
}

function sar(rows, threshold = 100000) {
  const report = suspicious(rows, threshold);
  return {
    generated_at: new Date().toISOString(),
    total_reports: report.transactions.length,
    reports: report.transactions.map((item) => ({
      report_id: `SAR-${Math.random().toString(36).slice(2, 10).toUpperCase()}`,
      organization_id: "local-storage",
      subject_account: item.user_details.user_id,
      suspicious_activity_type: ["HIGH_RISK_SCORE"],
      narrative_summary: `Transaction ${item.transaction_id} is flagged for review.`,
      transaction_details: [item],
      risk_score: item.risk_score,
      compliance_status: "UNDER_REVIEW",
      created_at: new Date().toISOString(),
    })),
  };
}

function exportBlob(rows, params = {}) {
  const threshold = num(params.regulatory_amount_threshold, 100000);
  const c = compliance(rows, threshold);
  const s = suspicious(rows, threshold);
  const sarReport = sar(rows, threshold);
  const payload = { compliance_report: c, suspicious_report: s, sar_report: sarReport };
  const format = String(params.export_format || "json").toLowerCase();
  if (format === "excel" || format === "xlsx") {
    const csv = ["transaction_id,user_id,risk_score,compliance_status"];
    c.transactions.forEach((item) => csv.push(`${item.transaction_id},${item.user_id},${item.risk_score},${item.compliance_status}`));
    return new Blob([csv.join("\n")], { type: "text/csv;charset=utf-8;" });
  }
  if (format === "pdf") {
    const text = `SecurePay AML Compliance Report\nTotal: ${c.total_transactions}\nSuspicious: ${c.suspicious_transactions}\nFraud Rate: ${c.fraud_rate}%`;
    return new Blob([text], { type: "application/pdf" });
  }
  if (format === "encrypted_xml" || format === "xml") {
    const xml = `<?xml version="1.0" encoding="UTF-8"?><compliance_export><payload>${btoa(JSON.stringify(payload))}</payload></compliance_export>`;
    return new Blob([xml], { type: "application/octet-stream" });
  }
  return new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
}

function realtime(rows) {
  const geo = geographic(rows);
  const clusterData = fraudClusters(rows);
  const high = rows.filter((row) => row.risk_score > 60).length;
  const ratio = rows.length ? (high / rows.length) * 100 : 0;
  return {
    alert_active: ratio > 40 || clusterData.meta.high_severity_clusters > 0,
    fraud_spike_percentage: Number(ratio.toFixed(2)),
    cluster_breach: clusterData.meta.high_severity_clusters > 0,
    flashing_markers: geo.points.filter((point) => point.heat_intensity >= 0.35).slice(0, 10).map((point) => ({
      lat: point.lat,
      lng: point.lng,
      heat_intensity: point.heat_intensity,
      risk_level: point.risk_level,
    })),
    alerts: [],
  };
}

export function localHeatmapFallback(path, params = {}, asBlob = false) {
  const rows = applyFilters(getTransactions().map(normalize), params);
  const threshold = num(params.regulatory_amount_threshold, 100000);
  if (asBlob || path.endsWith("/compliance-report/export")) return exportBlob(rows, params);
  if (path.endsWith("/geographic")) return geographic(rows);
  if (path.endsWith("/time-pattern")) return timePattern(rows);
  if (path.endsWith("/device-anomaly")) return deviceAnomaly(rows);
  if (path.endsWith("/fraud-clusters")) return fraudClusters(rows);
  if (path.endsWith("/predictive-risk")) return predictiveRisk(rows);
  if (path.endsWith("/zone-drilldown")) return zoneDrilldown(rows, params);
  if (path.endsWith("/realtime-status")) return realtime(rows);
  if (path.endsWith("/summary")) return summary(rows, params);
  if (path.endsWith("/compliance-report")) return compliance(rows, threshold);
  if (path.endsWith("/suspicious-transactions-report")) return suspicious(rows, threshold);
  if (path.endsWith("/sar")) return sar(rows, threshold);
  return {};
}
