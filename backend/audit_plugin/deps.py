from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, Header, HTTPException, Request, status

from security import get_current_user


@dataclass(slots=True)
class AuditContext:
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


def get_audit_context(
    user: dict = Depends(get_current_user),
    x_workspace_id: str | None = Header(default=None),
) -> AuditContext:
    user_id = str(user.get("uid") or user.get("user_id") or "unknown")
    role = _canonical_role(str(user.get("role") or "VIEWER"))
    organization_id = str(user.get("organization_id") or x_workspace_id or f"workspace:{user_id}")

    return AuditContext(user_id=user_id, role=role, organization_id=organization_id)


def require_roles(*roles: str) -> Callable[[AuditContext], AuditContext]:
    allowed = {role.upper() for role in roles}

    def _check(ctx: AuditContext = Depends(get_audit_context)) -> AuditContext:
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
