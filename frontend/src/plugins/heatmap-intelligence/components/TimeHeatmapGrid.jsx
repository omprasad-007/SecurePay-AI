import React, { useMemo } from "react";

function intensityColor(value) {
  const v = Math.max(0, Math.min(1, value || 0));
  const red = Math.round(30 + v * 190);
  const green = Math.round(180 - v * 130);
  const blue = Math.round(40 + (1 - v) * 40);
  return `rgb(${red}, ${green}, ${blue})`;
}

export default function TimeHeatmapGrid({ data }) {
  const grouped = useMemo(() => {
    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const byDay = Object.fromEntries(days.map((day) => [day, Array.from({ length: 24 }, () => null)]));
    (data?.matrix || []).forEach((cell) => {
      if (byDay[cell.day_name]) byDay[cell.day_name][cell.hour] = cell;
    });
    return byDay;
  }, [data]);

  return (
    <section className="hmi-panel">
      <h2 className="hmi-title">Time-Based Anomaly Heatmap</h2>
      <p className="hmi-subtitle">Hour vs day fraud intensity for spike detection windows.</p>
      <div style={{ marginTop: "0.9rem", overflowX: "auto" }}>
        {Object.entries(grouped).map(([day, cells]) => (
          <div key={day} style={{ display: "grid", gridTemplateColumns: "48px 1fr", gap: "0.4rem", marginBottom: "0.3rem" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--muted)", alignSelf: "center" }}>{day}</div>
            <div className="hmi-heat-grid">
              {cells.map((cell, index) => (
                <div
                  key={`${day}-${index}`}
                  className="hmi-heat-cell"
                  title={`${day} ${index}:00 | intensity ${cell?.fraud_intensity ?? 0}`}
                  style={{ background: intensityColor(cell?.fraud_intensity || 0) }}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

