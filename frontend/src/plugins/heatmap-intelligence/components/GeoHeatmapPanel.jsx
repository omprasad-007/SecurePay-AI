import React, { useMemo } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";

function riskColor(level) {
  if (level === "Critical") return "#7f1d1d";
  if (level === "High") return "#ef4444";
  if (level === "Medium") return "#f59e0b";
  return "#22c55e";
}

function radius(intensity) {
  return 8 + Math.min(32, (intensity || 0) * 24);
}

export default function GeoHeatmapPanel({ data, onZoneClick }) {
  const points = data?.points || [];
  const center = useMemo(() => {
    if (!points.length) return [20.5937, 78.9629];
    const lat = points.reduce((sum, item) => sum + item.lat, 0) / points.length;
    const lng = points.reduce((sum, item) => sum + item.lng, 0) / points.length;
    return [lat, lng];
  }, [points]);

  return (
    <section className="hmi-panel">
      <h2 className="hmi-title">Geospatial Fraud Heatmap</h2>
      <p className="hmi-subtitle">Green to dark-red intensity by fraud density and weighted risk.</p>

      <div className="hmi-map-wrap" style={{ marginTop: "0.8rem" }}>
        <MapContainer center={center} zoom={5} className="hmi-map" scrollWheelZoom>
          <TileLayer
            attribution="&copy; OpenStreetMap contributors"
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {points.map((point, idx) => (
            <CircleMarker
              key={`${point.lat}-${point.lng}-${idx}`}
              center={[point.lat, point.lng]}
              radius={radius(point.heat_intensity)}
              pathOptions={{
                color: riskColor(point.risk_level),
                fillColor: riskColor(point.risk_level),
                fillOpacity: 0.55,
              }}
              eventHandlers={{
                click: () => onZoneClick?.(point),
              }}
            >
              <Popup>
                <div style={{ minWidth: 180 }}>
                  <strong>{point.risk_level} Zone</strong>
                  <div>Risk Density: {point.risk_density}</div>
                  <div>Fraud Count: {point.fraud_count}</div>
                  <div>Avg Risk: {point.avg_risk_score}</div>
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>

      <div className="hmi-legend">
        <div className="hmi-legend-item">
          <span className="hmi-dot hmi-dot-low" /> Low
        </div>
        <div className="hmi-legend-item">
          <span className="hmi-dot hmi-dot-medium" /> Medium
        </div>
        <div className="hmi-legend-item">
          <span className="hmi-dot hmi-dot-high" /> High
        </div>
        <div className="hmi-legend-item">
          <span className="hmi-dot hmi-dot-critical" /> Critical
        </div>
      </div>
    </section>
  );
}

