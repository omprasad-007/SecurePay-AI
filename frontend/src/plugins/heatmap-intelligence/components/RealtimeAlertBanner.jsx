import React from "react";

export default function RealtimeAlertBanner({ realtime }) {
  if (!realtime?.alert_active) return null;

  return (
    <div className="hmi-alert hmi-alert-flash">
      <strong>High Risk Audit Detected</strong>
      <p style={{ margin: "0.3rem 0 0", fontSize: "0.86rem" }}>
        Fraud spike: {realtime.fraud_spike_percentage?.toFixed?.(2) ?? realtime.fraud_spike_percentage}%.
        {realtime.cluster_breach ? " Geo cluster threshold breached." : ""}
      </p>
    </div>
  );
}

