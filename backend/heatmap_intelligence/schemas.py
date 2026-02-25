from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import settings


class HeatmapFilterQuery(BaseModel):
    start_date: date
    end_date: date
    risk_level: str | None = None
    min_amount: float | None = Field(default=None, ge=0)
    max_amount: float | None = Field(default=None, ge=0)
    user_segment: str | None = None
    device_type: str | None = None
    limit: int = Field(default=settings.default_limit, ge=1, le=settings.max_limit)

    @field_validator("end_date")
    @classmethod
    def validate_date_order(cls, value: date, info):
        start = info.data.get("start_date")
        if start and value < start:
            raise ValueError("end_date must be greater than or equal to start_date")
        span_days = (value - start).days + 1 if start else 1
        if span_days > settings.max_query_days:
            raise ValueError(f"date range exceeds max window of {settings.max_query_days} days")
        return value

    @field_validator("max_amount")
    @classmethod
    def validate_amount_range(cls, value: float | None, info):
        minimum = info.data.get("min_amount")
        if value is not None and minimum is not None and value < minimum:
            raise ValueError("max_amount must be greater than or equal to min_amount")
        return value

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, value: str | None):
        if value is None:
            return value
        normalized = value.strip().capitalize()
        if normalized not in {"Low", "Medium", "High", "Critical"}:
            raise ValueError("risk_level must be one of: Low, Medium, High, Critical")
        return normalized


class GeographicHeatPoint(BaseModel):
    lat: float
    lng: float
    risk_density: float
    fraud_count: int
    avg_risk_score: float
    heat_intensity: float
    risk_level: str


class GeographicHeatmapResponse(BaseModel):
    points: list[GeographicHeatPoint]
    meta: dict[str, Any]


class TimePatternCell(BaseModel):
    day_index: int
    day_name: str
    hour: int
    fraud_intensity: float
    fraud_count: int
    avg_risk_score: float


class TimePatternResponse(BaseModel):
    matrix: list[TimePatternCell]
    meta: dict[str, Any]


class DeviceAnomalyPoint(BaseModel):
    device_id: str
    device_type: str
    transaction_count: int
    login_frequency: float
    transaction_speed: float
    geo_mismatch_score: float
    ip_anomaly_score: float
    anomaly_score: float
    cluster_label: str
    anomaly_level: str


class DeviceAnomalyResponse(BaseModel):
    devices: list[DeviceAnomalyPoint]
    meta: dict[str, Any]


class FraudClusterRecord(BaseModel):
    cluster_id: str
    cluster_size: int
    users: list[str]
    shared_devices: list[str]
    shared_ips: list[str]
    shared_accounts: list[str]
    high_risk_ratio: float
    ring_risk_score: float
    summary: str | None = None
    detected_at: datetime


class FraudClustersResponse(BaseModel):
    clusters: list[FraudClusterRecord]
    meta: dict[str, Any]


class PredictiveRiskZoneRecord(BaseModel):
    city: str | None
    state: str | None
    country: str | None
    geo_latitude: float | None
    geo_longitude: float | None
    historical_density: float
    growth_rate: float
    transaction_growth_velocity: float
    predicted_risk_score: float
    label: str


class PredictiveRiskResponse(BaseModel):
    zones: list[PredictiveRiskZoneRecord]
    meta: dict[str, Any]


class ZoneDrilldownResponse(BaseModel):
    total_transactions: int
    fraud_percentage: float
    top_users: list[dict[str, Any]]
    top_devices: list[dict[str, Any]]
    risk_breakdown: dict[str, int]
    ai_summary: str


class RealtimeStatusResponse(BaseModel):
    alert_active: bool
    fraud_spike_percentage: float
    cluster_breach: bool
    flashing_markers: list[dict[str, Any]]
    alerts: list[dict[str, Any]]


class HeatmapSummaryResponse(BaseModel):
    overall_risk_score: float
    fraud_concentration_change_pct: float
    top_region: str
    top_time_window: str
    linked_device_pattern: str
    ai_summary: str
    timeline: list[dict[str, Any]]
    layers: dict[str, Any] | None = None


class ComplianceItem(BaseModel):
    transaction_id: str
    user_id: str
    risk_score: float
    risk_reasons: list[str]
    city: str | None
    country: str | None
    device_id: str | None
    cluster_id: str | None
    compliance_status: str


class ComplianceReportResponse(BaseModel):
    report_generated_at: datetime
    total_transactions: int
    suspicious_transactions: int
    fraud_rate: float
    top_suspicious_accounts: list[dict[str, Any]]
    transactions: list[ComplianceItem]
    executive_summary: str


class SuspiciousTransactionRecord(BaseModel):
    transaction_id: str
    user_details: dict[str, Any]
    risk_score: float
    risk_reasons: list[str]
    geo_data: dict[str, Any]
    device_fingerprint: str | None
    ml_probability: float
    fraud_cluster_id: str | None
    amount: float
    timestamp: str
    feature_categories: dict[str, Any] | None = None
    anomaly_score: float | None = None
    rule_based_score: float | None = None
    final_risk_level: str | None = None


class SuspiciousTransactionReportResponse(BaseModel):
    generated_at: str
    total_flagged: int
    transactions: list[SuspiciousTransactionRecord]


class SARRecord(BaseModel):
    report_id: str
    organization_id: str
    subject_account: str | None
    suspicious_activity_type: list[str]
    narrative_summary: str
    transaction_details: list[dict[str, Any]]
    risk_score: float
    compliance_status: str
    created_at: str


class SARReportResponse(BaseModel):
    generated_at: str
    total_reports: int
    reports: list[SARRecord]
