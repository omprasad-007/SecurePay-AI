from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import AuditContext, require_roles
from ..repositories.audit_repository import list_alerts
from ..schemas import AlertRecord, AlertsResponse

router = APIRouter(prefix="/api", tags=["audit-alerts"])


@router.get("/alerts", response_model=AlertsResponse)
def get_alerts(
    limit: int = Query(default=50, ge=1, le=250),
    ctx: AuditContext = Depends(require_roles("SUPER_ADMIN", "ORG_ADMIN", "ANALYST", "VIEWER")),
    db: Session = Depends(get_db),
):
    rows = list_alerts(db, ctx, limit=limit)
    alerts = [AlertRecord.model_validate(row) for row in rows]
    unread = sum(1 for alert in alerts if not alert.is_read)
    return AlertsResponse(unread_count=unread, total=len(alerts), alerts=alerts)

