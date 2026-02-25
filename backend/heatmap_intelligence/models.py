from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class FraudHeatmapSnapshot(Base):
    __tablename__ = "fraud_heatmap_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    layer_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class FraudCluster(Base):
    __tablename__ = "fraud_clusters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    cluster_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    users: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    shared_devices: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    shared_ips: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    shared_accounts: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    ring_risk_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    cluster_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class PredictiveRiskZone(Base):
    __tablename__ = "predictive_risk_zones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    city: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    geo_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    geo_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    historical_density: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    growth_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    transaction_growth_velocity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    predicted_risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    label: Mapped[str] = mapped_column(String(80), nullable=False, default="Monitor")
    window_start: Mapped[date] = mapped_column(Date, nullable=False)
    window_end: Mapped[date] = mapped_column(Date, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class HeatmapAlert(Base):
    __tablename__ = "heatmap_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    alert_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="HIGH")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


Index("ix_heatmap_snapshots_org_dates", FraudHeatmapSnapshot.organization_id, FraudHeatmapSnapshot.start_date, FraudHeatmapSnapshot.end_date)
Index("ix_fraud_clusters_org_cluster", FraudCluster.organization_id, FraudCluster.cluster_id)
Index("ix_predictive_risk_org_window", PredictiveRiskZone.organization_id, PredictiveRiskZone.window_start, PredictiveRiskZone.window_end)
Index("ix_heatmap_alerts_org_created", HeatmapAlert.organization_id, HeatmapAlert.created_at)

