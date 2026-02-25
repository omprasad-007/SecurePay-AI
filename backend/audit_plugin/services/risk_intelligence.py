from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from ..deps import AuditContext
from ..repositories.audit_repository import (
    aggregate_metrics,
    high_risk_rows,
    pattern_counts,
    query_audit_rows,
    top_locations,
    top_suspicious_users,
    upsert_snapshot,
)
from ..schemas import RiskIntelligenceResponse, RiskRecord
from ..utils.date_math import risk_level, to_datetime_bounds
from .alert_engine import evaluate_alerts


def build_risk_intelligence(
    db: Session,
    ctx: AuditContext,
    start_date: date,
    end_date: date,
) -> RiskIntelligenceResponse:
    start_dt, end_dt = to_datetime_bounds(start_date, end_date)

    rows = query_audit_rows(db, ctx, start_dt, end_dt)
    metrics = aggregate_metrics(rows)
    flagged = high_risk_rows(db, ctx, start_dt, end_dt, threshold=60.0, limit=200)

    patterns_map = pattern_counts(flagged if flagged else rows)
    common_patterns = [
        {"pattern": key, "count": value}
        for key, value in sorted(patterns_map.items(), key=lambda item: item[1], reverse=True)[:6]
    ]

    overall_risk_score = float(metrics["avg_risk"])
    classification = risk_level(overall_risk_score)
    high_risk_pct = float(metrics["high_risk_pct"])

    evaluate_alerts(
        db=db,
        ctx=ctx,
        overall_risk_score=overall_risk_score,
        high_risk_percentage=high_risk_pct,
        start_date=start_date,
        end_date=end_date,
    )

    upsert_snapshot(
        db=db,
        ctx=ctx,
        start_date=start_date,
        end_date=end_date,
        overall_risk_score=overall_risk_score,
        high_risk_percentage=high_risk_pct,
        fraud_rate=float(metrics["fraud_rate"]),
        transaction_volume=int(metrics["total"]),
        trend_direction="UP" if overall_risk_score > 60 else "STABLE",
        details={
            "high_risk_count": int(metrics["high_risk_count"]),
            "common_fraud_patterns": common_patterns,
        },
    )

    risk_records = [
        RiskRecord(
            transaction_id=item.transaction_id,
            merchant_name=item.merchant_name,
            transaction_amount=float(item.transaction_amount),
            transaction_status=item.transaction_status,
            risk_score=float(item.risk_score),
            risk_level=item.risk_level,
            risk_reasons=list(item.risk_reasons or []),
            transaction_datetime=item.transaction_datetime,
            city=item.city,
        )
        for item in flagged
    ]

    return RiskIntelligenceResponse(
        overall_risk_score=round(overall_risk_score, 2),
        risk_classification=classification,
        high_risk_percentage=round(high_risk_pct, 2),
        top_suspicious_users=top_suspicious_users(db, ctx, start_dt, end_dt),
        high_risk_locations=top_locations(db, ctx, start_dt, end_dt),
        common_fraud_patterns=common_patterns,
        flagged_transactions=risk_records,
    )

