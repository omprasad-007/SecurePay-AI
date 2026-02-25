from __future__ import annotations

from fastapi import APIRouter, FastAPI

from .heatmap import router as heatmap_router

router = APIRouter()
router.include_router(heatmap_router)


def register_routers(app: FastAPI) -> None:
    app.include_router(router)


__all__ = ["router", "register_routers"]

