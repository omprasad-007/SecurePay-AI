from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, Header, HTTPException, Request, status

from security import get_current_user

from .config import settings


@dataclass(slots=True)
class HeatmapContext:
    user_id: str
    role: str
    organization_id: str


def _canonical_role(value: str | None) -> str:
    role = (value or "VIEWER").strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "ADMIN": "ORG_ADMIN",
        "ORGADMIN": "ORG_ADMIN",
        "RISK_ANALYST": "ANALYST",
        "AUDITOR": "VIEWER",
        "USER": "VIEWER",
    }
    return aliases.get(role, role)


def get_heatmap_context(
    user: dict = Depends(get_current_user),
    x_workspace_id: str | None = Header(default=None),
) -> HeatmapContext:
    user_id = str(user.get("uid") or user.get("user_id") or "unknown")
    role = _canonical_role(str(user.get("role") or "VIEWER"))
    organization_id = str(user.get("organization_id") or x_workspace_id or f"workspace:{user_id}")
    return HeatmapContext(user_id=user_id, role=role, organization_id=organization_id)


def require_roles(*roles: str) -> Callable[[HeatmapContext], HeatmapContext]:
    allowed = {item.upper() for item in roles}

    def _check(ctx: HeatmapContext = Depends(get_heatmap_context)) -> HeatmapContext:
        if ctx.role.upper() not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return ctx

    return _check


def request_ip(request: Request | None) -> str:
    if request is None:
        return "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


_rate_lock = threading.Lock()
_rate_window_seconds = 60
_rate_hits: dict[str, deque[float]] = defaultdict(deque)


def enforce_rate_limit(
    request: Request,
    ctx: HeatmapContext = Depends(get_heatmap_context),
) -> HeatmapContext:
    key = f"{ctx.organization_id}:{ctx.user_id}:{request.url.path}"
    now = time.time()
    with _rate_lock:
        hits = _rate_hits[key]
        while hits and now - hits[0] > _rate_window_seconds:
            hits.popleft()
        if len(hits) >= settings.rate_limit_per_minute:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Heatmap API rate limit exceeded")
        hits.append(now)
    return ctx
