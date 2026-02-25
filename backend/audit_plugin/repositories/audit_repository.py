from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from ..deps import AuditContext
from ..models import AuditAdvanced, AuditAlert, AuditReport, RiskSnapshot


def store_audit_rows(db: Session, ctx: AuditContext, rows: Iterable[dict], source_file: str) -> list[AuditAdvanced]:
    created = []
    for row in rows:
        entry = AuditAdvanced(
            organization_id=ctx.organization_id,
            user_id=ctx.user_id,
            transaction_id=row["transaction_id"],
            sender_name=row.get("sender_name"),
            receiver_name=row.get("receiver_name"),
            merchant_name=row.get("merchant_name"),
            transaction_amount=float(row.get("transaction_amount") or 0.0),
            currency=row.get("currency") or "INR",
            transaction_status=row.get("transaction_status"),
            risk_score=float(row.get("risk_score") or 0.0),
            risk_level=row.get("risk_level") or "Low",
            risk_reasons=row.get("risk_reasons") or [],
            transaction_datetime=row["transaction_datetime"],
            city=row.get("city"),
            state=row.get("state"),
            country=row.get("country"),
            geo_latitude=row.get("geo_latitude"),
            geo_longitude=row.get("geo_longitude"),
            device_id=row.get("device_id"),
            ip_address=row.get("ip_address"),
            source_file=source_file,
        )
        db.add(entry)
        created.append(entry)

    db.commit()
    for entry in created:
        db.refresh(entry)
    return created


def history_rows(db: Session, ctx: AuditContext, limit: int = 5000) -> list[AuditAdvanced]:
    return db.execute(
        select(AuditAdvanced)
        .where(AuditAdvanced.organization_id == ctx.organization_id)
        .order_by(desc(AuditAdvanced.transaction_datetime))
        .limit(limit)
    ).scalars().all()


def query_audit_rows(
    db: Session,
    ctx: AuditContext,
    start_dt: datetime,
    end_dt: datetime,
    risk_level: str | None = None,
    transaction_status: str | None = None,
    user_id: str | None = None,
) -> list[AuditAdvanced]:
    query = select(AuditAdvanced).where(
        AuditAdvanced.organization_id == ctx.organization_id,
        AuditAdvanced.transaction_datetime >= start_dt,
        AuditAdvanced.transaction_datetime <= end_dt,
    )

    if risk_level:
        query = query.where(AuditAdvanced.risk_level.ilike(risk_level))
    if transaction_status:
        query = query.where(AuditAdvanced.transaction_status.ilike(transaction_status))
    if user_id:
        query = query.where(AuditAdvanced.user_id == user_id)

    return db.execute(query.order_by(desc(AuditAdvanced.transaction_datetime))).scalars().all()


def high_risk_rows(
    db: Session,
    ctx: AuditContext,
    start_dt: datetime,
    end_dt: datetime,
    threshold: float = 60.0,
    limit: int = 100,
) -> list[AuditAdvanced]:
    return db.execute(
        select(AuditAdvanced)
        .where(
            AuditAdvanced.organization_id == ctx.organization_id,
            AuditAdvanced.transaction_datetime >= start_dt,
            AuditAdvanced.transaction_datetime <= end_dt,
            AuditAdvanced.risk_score > threshold,
        )
        .order_by(desc(AuditAdvanced.risk_score), desc(AuditAdvanced.transaction_datetime))
        .limit(limit)
    ).scalars().all()


def aggregate_metrics(rows: list[AuditAdvanced]) -> dict:
    total = len(rows)
    if total == 0:
        return {
            "total": 0,
            "avg_risk": 0.0,
            "high_risk_pct": 0.0,
            "fraud_rate": 0.0,
            "high_risk_count": 0,
        }

    high_risk = [row for row in rows if row.risk_score > 60]
    avg_risk = sum(row.risk_score for row in rows) / total
    high_pct = len(high_risk) * 100 / total

    return {
        "total": total,
        "avg_risk": round(avg_risk, 2),
        "high_risk_pct": round(high_pct, 2),
        "fraud_rate": round(high_pct, 2),
        "high_risk_count": len(high_risk),
    }


def create_alert(
    db: Session,
    ctx: AuditContext,
    title: str,
    message: str,
    severity: str,
    trigger_payload: dict,
) -> AuditAlert:
    alert = AuditAlert(
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        title=title,
        message=message,
        severity=severity,
        trigger_payload=trigger_payload,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def list_alerts(db: Session, ctx: AuditContext, limit: int = 50) -> list[AuditAlert]:
    return db.execute(
        select(AuditAlert)
        .where(AuditAlert.organization_id == ctx.organization_id)
        .order_by(desc(AuditAlert.created_at))
        .limit(limit)
    ).scalars().all()


def create_report_log(
    db: Session,
    ctx: AuditContext,
    start_date,
    end_date,
    report_type: str,
    file_format: str,
    file_name: str | None,
    email_to: str | None,
    status: str,
    meta: dict,
) -> AuditReport:
    row = AuditReport(
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        start_date=start_date,
        end_date=end_date,
        report_type=report_type,
        file_format=file_format,
        file_name=file_name,
        email_to=email_to,
        status=status,
        meta=meta,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def upsert_snapshot(
    db: Session,
    ctx: AuditContext,
    start_date,
    end_date,
    overall_risk_score: float,
    high_risk_percentage: float,
    fraud_rate: float,
    transaction_volume: int,
    trend_direction: str,
    details: dict,
) -> RiskSnapshot:
    existing = db.execute(
        select(RiskSnapshot).where(
            RiskSnapshot.organization_id == ctx.organization_id,
            RiskSnapshot.user_id == ctx.user_id,
            RiskSnapshot.snapshot_start == start_date,
            RiskSnapshot.snapshot_end == end_date,
        )
    ).scalar_one_or_none()

    if existing:
        existing.overall_risk_score = overall_risk_score
        existing.high_risk_percentage = high_risk_percentage
        existing.fraud_rate = fraud_rate
        existing.transaction_volume = transaction_volume
        existing.trend_direction = trend_direction
        existing.details = details
        db.commit()
        db.refresh(existing)
        return existing

    snapshot = RiskSnapshot(
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        snapshot_start=start_date,
        snapshot_end=end_date,
        overall_risk_score=overall_risk_score,
        high_risk_percentage=high_risk_percentage,
        fraud_rate=fraud_rate,
        transaction_volume=transaction_volume,
        trend_direction=trend_direction,
        details=details,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def top_suspicious_users(db: Session, ctx: AuditContext, start_dt: datetime, end_dt: datetime, limit: int = 5) -> list[dict]:
    rows = db.execute(
        select(
            AuditAdvanced.user_id,
            func.count(AuditAdvanced.id).label("tx_count"),
            func.avg(AuditAdvanced.risk_score).label("avg_risk"),
        )
        .where(
            AuditAdvanced.organization_id == ctx.organization_id,
            AuditAdvanced.transaction_datetime >= start_dt,
            AuditAdvanced.transaction_datetime <= end_dt,
        )
        .group_by(AuditAdvanced.user_id)
        .order_by(desc("avg_risk"))
        .limit(limit)
    ).all()

    return [
        {"user_id": row.user_id, "transaction_count": int(row.tx_count), "average_risk": round(float(row.avg_risk or 0), 2)}
        for row in rows
    ]


def top_locations(db: Session, ctx: AuditContext, start_dt: datetime, end_dt: datetime, limit: int = 5) -> list[dict]:
    rows = db.execute(
        select(
            AuditAdvanced.city,
            func.count(AuditAdvanced.id).label("high_risk_count"),
            func.avg(AuditAdvanced.risk_score).label("avg_risk"),
        )
        .where(
            AuditAdvanced.organization_id == ctx.organization_id,
            AuditAdvanced.transaction_datetime >= start_dt,
            AuditAdvanced.transaction_datetime <= end_dt,
            AuditAdvanced.risk_score > 60,
        )
        .group_by(AuditAdvanced.city)
        .order_by(desc("high_risk_count"))
        .limit(limit)
    ).all()

    return [
        {"city": row.city or "Unknown", "high_risk_count": int(row.high_risk_count), "average_risk": round(float(row.avg_risk or 0), 2)}
        for row in rows
    ]


def pattern_counts(rows: list[AuditAdvanced]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for reason in row.risk_reasons or []:
            counts[reason] = counts.get(reason, 0) + 1
    return counts
