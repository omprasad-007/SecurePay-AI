from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class AuditAdvanced(Base):
    __tablename__ = "audits_advanced"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    transaction_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    sender_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    receiver_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    merchant_name: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    transaction_amount: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    transaction_status: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    risk_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    transaction_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    geo_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    geo_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    device_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class AuditAlert(Base):
    __tablename__ = "audit_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False, default="HIGH")
    trigger_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AuditReport(Base):
    __tablename__ = "audit_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    report_type: Mapped[str] = mapped_column(String(40), nullable=False, default="AUDIT_EXPORT")
    file_format: Mapped[str] = mapped_column(String(20), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_to: Mapped[str | None] = mapped_column(String(320), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="GENERATED")
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RiskSnapshot(Base):
    __tablename__ = "risk_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    snapshot_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    snapshot_end: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    overall_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    high_risk_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    fraud_rate: Mapped[float] = mapped_column(Float, nullable=False)
    transaction_volume: Mapped[int] = mapped_column(Integer, nullable=False)
    trend_direction: Mapped[str] = mapped_column(String(20), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


Index("ix_audits_advanced_org_user", AuditAdvanced.organization_id, AuditAdvanced.user_id)
Index("ix_audits_advanced_org_date", AuditAdvanced.organization_id, AuditAdvanced.transaction_datetime)
Index("ix_audit_alerts_org_user", AuditAlert.organization_id, AuditAlert.user_id)
Index("ix_risk_snapshots_org_date", RiskSnapshot.organization_id, RiskSnapshot.snapshot_start, RiskSnapshot.snapshot_end)
