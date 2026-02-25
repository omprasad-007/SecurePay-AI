from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..deps import AuditContext
from ..models import AuditAlert
from ..repositories.audit_repository import create_alert


ALERT_TITLE = "High Risk Audit Detected"


def evaluate_alerts(
    db: Session,
    ctx: AuditContext,
    overall_risk_score: float,
    high_risk_percentage: float,
    start_date,
    end_date,
) -> AuditAlert | None:
    should_alert = overall_risk_score > 70 or high_risk_percentage > 25
    if not should_alert:
        return None

    cooldown = datetime.utcnow() - timedelta(hours=1)
    recent = db.execute(
        select(AuditAlert).where(
            and_(
                AuditAlert.organization_id == ctx.organization_id,
                AuditAlert.title == ALERT_TITLE,
                AuditAlert.created_at >= cooldown,
            )
        )
    ).scalar_one_or_none()
    if recent:
        return recent

    message = (
        "High Risk Audit Detected: risk metrics crossed safety threshold. "
        f"overall_risk={overall_risk_score:.2f}, high_risk_pct={high_risk_percentage:.2f}."
    )

    return create_alert(
        db,
        ctx,
        title=ALERT_TITLE,
        message=message,
        severity="HIGH",
        trigger_payload={
            "start_date": str(start_date),
            "end_date": str(end_date),
            "overall_risk_score": round(overall_risk_score, 2),
            "high_risk_percentage": round(high_risk_percentage, 2),
        },
    )
