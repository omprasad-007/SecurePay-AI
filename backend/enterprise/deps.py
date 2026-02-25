from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import User, UserRole
from .security import TokenPayload, decode_token


@dataclass(slots=True)
class Principal:
    user_id: str
    email: str
    role: UserRole
    organization_id: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return authorization.removeprefix("Bearer ").strip()


def get_current_principal(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Principal:
    token = _extract_bearer(authorization)

    try:
        payload: TokenPayload = decode_token(token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = db.get(User, payload.sub)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return Principal(
        user_id=user.id,
        email=user.email,
        role=user.role,
        organization_id=user.organization_id,
    )


def require_roles(*roles: UserRole) -> Callable[[Principal], Principal]:
    allowed = set(roles)

    def _checker(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.role == UserRole.SUPER_ADMIN:
            return principal
        if principal.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return principal

    return _checker


def get_client_ip(request: Request | None) -> str:
    if request is None:
        return "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
