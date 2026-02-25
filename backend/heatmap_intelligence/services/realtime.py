from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from ..config import settings
from ..deps import HeatmapContext
from ..repositories.heatmap_repository import (
    create_heatmap_alert,
    fetch_hourly_high_risk_counts,
    fetch_transactions,
    latest_alert_by_type,
    list_recent_alerts,
)
from ..schemas import HeatmapFilterQuery, RealtimeStatusResponse
from .clustering import detect_fraud_clusters
from .density_engine import build_geographic_heatmap


def _high_risk_ratio(item: dict) -> float:
    total = max(1, int(item.get("total", 0)))
    return (float(item.get("high_risk", 0)) / total) * 100.0


def build_realtime_status(db: Session, ctx: HeatmapContext) -> RealtimeStatusResponse:
    hourly = fetch_hourly_high_risk_counts(db, ctx, hours=2)
    hourly_sorted = sorted(hourly, key=lambda item: item["hour_key"])

    fraud_spike = 0.0
    if len(hourly_sorted) >= 2:
        prev = _high_risk_ratio(hourly_sorted[-2])
        curr = _high_risk_ratio(hourly_sorted[-1])
        if prev == 0:
            fraud_spike = 100.0 if curr > 0 else 0.0
        else:
            fraud_spike = ((curr - prev) / prev) * 100.0

    today = date.today()
    recent_filter = HeatmapFilterQuery(
        start_date=today - timedelta(days=1),
        end_date=today,
        limit=2000,
    )
    recent_rows = fetch_transactions(db, ctx, recent_filter)
    geo = build_geographic_heatmap(recent_rows)
    clusters = detect_fraud_clusters(recent_rows)

    cluster_breach = sum(1 for cluster in clusters.clusters if cluster.ring_risk_score > 70) >= settings.cluster_alert_threshold
    spike_breach = fraud_spike > settings.spike_increase_threshold_pct
    alert_active = spike_breach or cluster_breach

    if alert_active:
        alert_type = "FRAUD_SPIKE" if spike_breach else "GEO_CLUSTER_BREACH"
        if latest_alert_by_type(db, ctx, alert_type, within_minutes=30) is None:
            message = (
                "High-risk activity spike detected."
                if spike_breach
                else "Critical geo cluster threshold exceeded."
            )
            create_heatmap_alert(
                db=db,
                ctx=ctx,
                alert_type=alert_type,
                severity="CRITICAL",
                message=message,
                trigger_payload={
                    "fraud_spike_percentage": round(fraud_spike, 2),
                    "cluster_breach": cluster_breach,
                    "cluster_count": len(clusters.clusters),
                },
            )

    flashing_markers = [
        {
            "lat": point.lat,
            "lng": point.lng,
            "heat_intensity": point.heat_intensity,
            "risk_level": point.risk_level,
        }
        for point in geo.points[:10]
        if point.heat_intensity >= 0.35
    ]

    alerts = [
        {
            "id": row.id,
            "alert_type": row.alert_type,
            "severity": row.severity,
            "message": row.message,
            "created_at": row.created_at.isoformat(),
            "trigger_payload": row.trigger_payload,
        }
        for row in list_recent_alerts(db, ctx, limit=20)
    ]

    return RealtimeStatusResponse(
        alert_active=alert_active,
        fraud_spike_percentage=round(fraud_spike, 2),
        cluster_breach=cluster_breach,
        flashing_markers=flashing_markers,
        alerts=alerts,
    )

