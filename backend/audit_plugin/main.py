from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import register_routers


def create_app() -> FastAPI:
    app = FastAPI(title="SecurePay AI Audit Plugin", version="1.0.0")

    frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    allowed_origins = [item.strip() for item in frontend_origin.split(",") if item.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-User-Role", "X-Workspace-Id"],
    )

    @app.on_event("startup")
    def startup_event():
        Base.metadata.create_all(bind=engine)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "audit-plugin"}

    register_routers(app)
    return app


app = create_app()

