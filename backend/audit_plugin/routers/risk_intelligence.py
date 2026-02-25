from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import AuditContext, require_roles
from ..schemas import RiskIntelligenceResponse
from ..services.risk_intelligence import build_risk_intelligence
from ..utils.validators import validate_date_range

router = APIRouter(prefix="/api/risk", tags=["risk-intelligence"])


@router.get("/intelligence", response_model=RiskIntelligenceResponse)
def risk_intelligence(
    start_date: date = Query(...),
    end_date: date = Query(...),
    ctx: AuditContext = Depends(require_roles("SUPER_ADMIN", "ORG_ADMIN", "ANALYST", "VIEWER")),
    db: Session = Depends(get_db),
):
    validate_date_range(start_date, end_date)
    return build_risk_intelligence(db, ctx, start_date, end_date)

