from __future__ import annotations

from fastapi import APIRouter, FastAPI

from .alerts import router as alerts_router
from .audit import router as audit_router
from .risk_intelligence import router as risk_router

router = APIRouter()
router.include_router(audit_router)
router.include_router(risk_router)
router.include_router(alerts_router)


def register_routers(app: FastAPI) -> None:
    app.include_router(router)


__all__ = ["router", "register_routers"]
