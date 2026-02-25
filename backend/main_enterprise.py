from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from enterprise.config import settings
from enterprise.database import Base, engine
from enterprise.routers import (
    api_keys_router,
    audit_router,
    auth_router,
    organization_router,
    transactions_router,
    users_router,
)

app = FastAPI(title=settings.app_name, version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


_request_log: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    now = time.time()
    client_ip = request.client.host if request.client else "unknown"
    hits = _request_log[client_ip]

    while hits and now - hits[0] > 60:
        hits.popleft()

    if len(hits) >= settings.request_limit_per_minute:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

    hits.append(now)
    response = await call_next(request)
    return response


@app.middleware("http")
async def secure_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


app.include_router(auth_router)
app.include_router(transactions_router)
app.include_router(audit_router)
app.include_router(users_router)
app.include_router(organization_router)
app.include_router(api_keys_router)


@app.get("/")
def root():
    return {"status": "SecurePay AI Enterprise API online"}
