from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


from typing import Any, Optional


class DateRangeQuery(BaseModel):
    start_date: date
    end_date: date

    @field_validator("end_date")
    @classmethod
    def validate_range(cls, value: date, info):
        start = info.data.get("start_date")
        if start and value < start:
            raise ValueError("end_date must be greater than or equal to start_date")
        return value


class AuditExportQuery(DateRangeQuery):
    format: str = Field(default="csv")
    risk_level: str | None = None
    transaction_status: str | None = None
    user_id: str | None = None


class UploadSummary(BaseModel):
    uploaded_records: int
    stored_records: int
    flagged_records: int
    average_risk_score: float
    risk_level_distribution: dict[str, int]


class UploadResponse(BaseModel):
    success: bool = True
    preview: Optional[list[dict[str, Any]]] = None
    totalRows: Optional[int] = None
    summary: Optional[UploadSummary] = None
    message: str


class RiskRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: str
    merchant_name: str | None
    transaction_amount: float
    transaction_status: str | None
    risk_score: float
    risk_level: str
    risk_reasons: list[str]
    transaction_datetime: datetime
    city: str | None


class RiskIntelligenceResponse(BaseModel):
    overall_risk_score: float
    risk_classification: str
    high_risk_percentage: float
    top_suspicious_users: list[dict[str, Any]]
    high_risk_locations: list[dict[str, Any]]
    common_fraud_patterns: list[dict[str, Any]]
    flagged_transactions: list[RiskRecord]


class EmailReportRequest(DateRangeQuery):
    email: EmailStr


class EmailReportResponse(BaseModel):
    status: str
    report_id: str
    email: EmailStr


class AlertRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    message: str
    severity: str
    trigger_payload: dict[str, Any]
    is_read: bool
    is_resolved: bool
    created_at: datetime


class AlertsResponse(BaseModel):
    unread_count: int
    total: int
    alerts: list[AlertRecord]


class AuditSummaryResponse(BaseModel):
    start_date: date
    end_date: date
    transaction_volume: int
    fraud_rate: float
    overall_risk_score: float
    transaction_volume_change_pct: float
    fraud_rate_change_pct: float
    risk_trend_direction: str
    ai_summary: str


class CompareSeriesPoint(BaseModel):
    label: str
    volume: int
    fraud_rate: float
    overall_risk_score: float


class AuditCompareResponse(BaseModel):
    current_period: CompareSeriesPoint
    previous_period: CompareSeriesPoint
    delta: dict[str, float]
    chart: dict[str, list[dict[str, float | str]]]
