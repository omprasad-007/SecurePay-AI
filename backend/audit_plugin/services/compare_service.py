from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from ..deps import AuditContext
from ..repositories.audit_repository import aggregate_metrics, query_audit_rows
from ..schemas import AuditCompareResponse, CompareSeriesPoint
from ..utils.date_math import previous_period, to_datetime_bounds


def _delta(current: float, previous: float) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return ((current - previous) / previous) * 100


def build_compare(db: Session, ctx: AuditContext, start_date: date, end_date: date) -> AuditCompareResponse:
    prev_start, prev_end = previous_period(start_date, end_date)

    current_rows = query_audit_rows(db, ctx, *to_datetime_bounds(start_date, end_date))
    previous_rows = query_audit_rows(db, ctx, *to_datetime_bounds(prev_start, prev_end))

    current = aggregate_metrics(current_rows)
    previous = aggregate_metrics(previous_rows)

    current_point = CompareSeriesPoint(
        label="Current",
        volume=int(current["total"]),
        fraud_rate=float(current["fraud_rate"]),
        overall_risk_score=float(current["avg_risk"]),
    )
    previous_point = CompareSeriesPoint(
        label="Previous",
        volume=int(previous["total"]),
        fraud_rate=float(previous["fraud_rate"]),
        overall_risk_score=float(previous["avg_risk"]),
    )

    return AuditCompareResponse(
        current_period=current_point,
        previous_period=previous_point,
        delta={
            "volume_change_pct": round(_delta(current["total"], previous["total"]), 2),
            "fraud_rate_change_pct": round(_delta(current["fraud_rate"], previous["fraud_rate"]), 2),
            "risk_score_change_pct": round(_delta(current["avg_risk"], previous["avg_risk"]), 2),
        },
        chart={
            "bar": [
                {"label": "Previous", "volume": previous_point.volume},
                {"label": "Current", "volume": current_point.volume},
            ],
            "line": [
                {"label": "Previous", "fraud_rate": previous_point.fraud_rate, "risk_score": previous_point.overall_risk_score},
                {"label": "Current", "fraud_rate": current_point.fraud_rate, "risk_score": current_point.overall_risk_score},
            ],
        },
    )
