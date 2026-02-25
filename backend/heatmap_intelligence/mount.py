from __future__ import annotations

from fastapi import FastAPI

from .database import Base, engine
from .routers import register_routers


def mount_heatmap_intelligence(app: FastAPI) -> None:
    Base.metadata.create_all(bind=engine)
    register_routers(app)

