from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

SourceBase = declarative_base()


class AuditSourceTransaction(SourceBase):
    __tablename__ = "audits_advanced"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    transaction_id: Mapped[str] = mapped_column(String(120), nullable=False)
    merchant_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    transaction_amount: Mapped[float] = mapped_column(Float, nullable=False)
    transaction_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    transaction_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    geo_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    geo_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

