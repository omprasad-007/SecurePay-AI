from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from models.risk_overview import build_risk_overview
from security import get_current_user

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/overview")
async def risk_overview(
    history: str | None = Query(default=None),
    user: dict[str, Any] = Depends(get_current_user),
):
    try:
        return build_risk_overview(history, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
