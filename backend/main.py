from __future__ import annotations

import logging
import os
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routes.predict import router as predict_router
from routes.analytics import router as analytics_router
from routes.feedback import router as feedback_router
from routes.reports import router as reports_router
from routes.excel_upload import router as excel_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("securepay")

app = FastAPI(title="SecurePay AI", version="1.0.0")


def _allowed_origins() -> list[str]:
    configured = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173,http://localhost:5174")
    return [item.strip() for item in configured.split(",") if item.strip()]


origins = _allowed_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))
request_log: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60

    hits = request_log[client_ip]
    while hits and now - hits[0] > window:
        hits.popleft()
    if len(hits) >= RATE_LIMIT:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

    hits.append(now)
    response = await call_next(request)
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    logger.info("%s %s %s", request.method, request.url.path, response.status_code)
    return response


@app.middleware("http")
async def jwt_verification_middleware(request: Request, call_next):
    if os.getenv("ALLOW_INSECURE_DEV", "true").lower() == "true":
        return await call_next(request)
    if request.method == "OPTIONS":
        return await call_next(request)
    if request.url.path in {"/", "/docs", "/openapi.json", "/redoc"}:
        return await call_next(request)
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        response = JSONResponse(status_code=401, content={"detail": "JWT token missing"})
        origin = request.headers.get("origin")
        if origin and origin in origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
        return response
    return await call_next(request)


app.include_router(predict_router)
app.include_router(analytics_router)
app.include_router(feedback_router)
app.include_router(reports_router)
app.include_router(excel_router)


@app.get("/")
async def root():
    return {"status": "SecurePay AI backend running"}
