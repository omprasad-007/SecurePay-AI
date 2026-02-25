import React, { useCallback, useEffect, useMemo, useState } from "react";
import "leaflet/dist/leaflet.css";
import "../styles.css";
import FilterPanel from "../components/FilterPanel";
import GeoHeatmapPanel from "../components/GeoHeatmapPanel";
import TimeHeatmapGrid from "../components/TimeHeatmapGrid";
import DeviceAnomalyPanel from "../components/DeviceAnomalyPanel";
import FraudClustersPanel from "../components/FraudClustersPanel";
import FraudRingGraphPanel from "../components/FraudRingGraphPanel";
import PredictiveZonesPanel from "../components/PredictiveZonesPanel";
import SummaryPanel from "../components/SummaryPanel";
import ComplianceReportsPanel from "../components/ComplianceReportsPanel";
import DrilldownModal from "../components/DrilldownModal";
import RealtimeAlertBanner from "../components/RealtimeAlertBanner";
import RealtimeStatusPanel from "../components/RealtimeStatusPanel";
import { useHeatmapFilters } from "../hooks/useHeatmapFilters";
import {
  getComplianceReport,
  getDeviceAnomaly,
  getFraudClusters,
  getGeographicHeatmap,
  getPredictiveRisk,
  getRealtimeStatus,
  getSarReport,
  getSummary,
  getSuspiciousTransactionsReport,
  getTimePattern,
  getZoneDrilldown,
} from "../services/heatmapApi";

export default function FraudHeatmapIntelligencePage() {
  const { filters, normalizedFilters, setField, refresh, reset, refreshKey } = useHeatmapFilters();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [geographic, setGeographic] = useState(null);
  const [timePattern, setTimePattern] = useState(null);
  const [deviceAnomaly, setDeviceAnomaly] = useState(null);
  const [clusters, setClusters] = useState(null);
  const [predictive, setPredictive] = useState(null);
  const [realtime, setRealtime] = useState(null);
  const [summary, setSummary] = useState(null);
  const [compliance, setCompliance] = useState(null);
  const [suspiciousReport, setSuspiciousReport] = useState(null);
  const [sarReport, setSarReport] = useState(null);
  const [drilldown, setDrilldown] = useState(null);
  const [drilldownOpen, setDrilldownOpen] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [
        geoRes,
        timeRes,
        deviceRes,
        clusterRes,
        predictiveRes,
        realtimeRes,
        summaryRes,
        complianceRes,
        suspiciousRes,
        sarRes
      ] = await Promise.all([
        getGeographicHeatmap(normalizedFilters),
        getTimePattern(normalizedFilters),
        getDeviceAnomaly(normalizedFilters),
        getFraudClusters(normalizedFilters),
        getPredictiveRisk(normalizedFilters),
        getRealtimeStatus(),
        getSummary(normalizedFilters),
        getComplianceReport(normalizedFilters),
        getSuspiciousTransactionsReport(normalizedFilters),
        getSarReport(normalizedFilters),
      ]);

      setGeographic(geoRes);
      setTimePattern(timeRes);
      setDeviceAnomaly(deviceRes);
      setClusters(clusterRes);
      setPredictive(predictiveRes);
      setRealtime(realtimeRes);
      setSummary(summaryRes);
      setCompliance(complianceRes);
      setSuspiciousReport(suspiciousRes);
      setSarReport(sarRes);
    } catch (err) {
      setError(err?.message || "Failed to load heatmap intelligence data.");
    } finally {
      setLoading(false);
    }
  }, [normalizedFilters]);

  useEffect(() => {
    loadData();
  }, [refreshKey]); // eslint-disable-line react-hooks/exhaustive-deps

  const onZoneClick = useCallback(
    async (point) => {
      try {
        const payload = await getZoneDrilldown({
          lat: point.lat,
          lng: point.lng,
          start_date: normalizedFilters.start_date,
          end_date: normalizedFilters.end_date,
        });
        setDrilldown(payload);
        setDrilldownOpen(true);
      } catch (err) {
        setError(err?.message || "Failed to load drill-down data.");
      }
    },
    [normalizedFilters.end_date, normalizedFilters.start_date]
  );

  const hasData = useMemo(() => (geographic?.points?.length || 0) > 0, [geographic]);

  return (
    <div className="space-y-4">
      <div className="card" style={{ padding: "1rem 1.1rem" }}>
        <h1 style={{ margin: 0, fontSize: "1.35rem", fontWeight: 700 }}>Fraud Heatmap Intelligence</h1>
        <p className="text-muted" style={{ marginTop: "0.35rem" }}>
          Real-time geospatial fraud density, AI clustering, predictive risk zones, and compliance-grade drill-down analytics.
        </p>
      </div>

      {error && (
        <div className="hmi-alert">
          <strong>Error:</strong> {error}
        </div>
      )}

      <RealtimeAlertBanner realtime={realtime} />

      <div className="hmi-layout">
        <aside className="hmi-column">
          <FilterPanel
            filters={filters}
            onChange={setField}
            onApply={refresh}
            onReset={() => {
              reset();
              refresh();
            }}
            loading={loading}
          />
          <RealtimeStatusPanel realtime={realtime} />
        </aside>

        <main className="hmi-column">
          <GeoHeatmapPanel data={geographic} onZoneClick={onZoneClick} />
          <TimeHeatmapGrid data={timePattern} />
          <DeviceAnomalyPanel data={deviceAnomaly} />
          <FraudClustersPanel data={clusters} />
          <FraudRingGraphPanel graph={summary?.layers?.fraud_ring_visualization} />
          <PredictiveZonesPanel data={predictive} />
          {!hasData && !loading && (
            <div className="hmi-panel">
              <p className="hmi-subtitle">No geolocation transactions available for selected filters.</p>
            </div>
          )}
        </main>

        <aside className="hmi-column hmi-summary-column">
          <SummaryPanel summary={summary} compliance={compliance} />
        </aside>
      </div>

      <DrilldownModal open={drilldownOpen} data={drilldown} onClose={() => setDrilldownOpen(false)} />

      <ComplianceReportsPanel
        filters={normalizedFilters}
        compliance={compliance}
        suspiciousReport={suspiciousReport}
        sarReport={sarReport}
      />
    </div>
  );
}
