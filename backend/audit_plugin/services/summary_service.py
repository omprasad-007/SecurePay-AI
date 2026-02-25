from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from ..deps import AuditContext
from ..repositories.audit_repository import aggregate_metrics, query_audit_rows
from ..schemas import AuditSummaryResponse
from ..utils.date_math import previous_period, to_datetime_bounds


def _change_pct(current: float, previous: float) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return ((current - previous) / previous) * 100


def _trend_label(current_risk: float, previous_risk: float) -> str:
    if current_risk > previous_risk + 3:
        return "UP"
    if current_risk < previous_risk - 3:
        return "DOWN"
    return "STABLE"


def _ai_summary(volume_change: float, fraud_change: float, trend: str, current_high_pct: float) -> str:
    direction = "increase" if volume_change >= 0 else "decrease"
    fraud_direction = "increase" if fraud_change >= 0 else "decrease"

    concentration = "late-night transactions and new device logins" if current_high_pct > 25 else "standard operational windows"

    return (
        f"This audit period shows {abs(volume_change):.1f}% abnormal transaction {direction} compared to previous period. "
        f"Fraud rate shows a {abs(fraud_change):.1f}% {fraud_direction} trend with risk direction {trend}. "
        f"High-risk activity is concentrated in {concentration}."
    )


def build_audit_summary(db: Session, ctx: AuditContext, start_date: date, end_date: date) -> AuditSummaryResponse:
    prev_start, prev_end = previous_period(start_date, end_date)

    current_rows = query_audit_rows(db, ctx, *to_datetime_bounds(start_date, end_date))
    previous_rows = query_audit_rows(db, ctx, *to_datetime_bounds(prev_start, prev_end))

    current = aggregate_metrics(current_rows)
    previous = aggregate_metrics(previous_rows)

    volume_change = _change_pct(current["total"], previous["total"])
    fraud_change = _change_pct(current["fraud_rate"], previous["fraud_rate"])
    trend = _trend_label(current["avg_risk"], previous["avg_risk"])

    summary = _ai_summary(volume_change, fraud_change, trend, current["high_risk_pct"])

    return AuditSummaryResponse(
        start_date=start_date,
        end_date=end_date,
        transaction_volume=int(current["total"]),
        fraud_rate=float(current["fraud_rate"]),
        overall_risk_score=float(current["avg_risk"]),
        transaction_volume_change_pct=round(volume_change, 2),
        fraud_rate_change_pct=round(fraud_change, 2),
        risk_trend_direction=trend,
        ai_summary=summary,
    )
