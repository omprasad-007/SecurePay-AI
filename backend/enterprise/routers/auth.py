from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_db
from ..models import InviteStatus, Organization, OrganizationInvite, User, UserRole
from ..schemas import AuthLoginRequest, AuthLoginResponse, AuthRefreshRequest, TokenPair
from ..security import create_access_token, create_refresh_token, decode_token, verify_google_id_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:140] or f"org-{uuid.uuid4().hex[:10]}"


def _issue_tokens(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id, user.role.value, user.organization_id),
        refresh_token=create_refresh_token(user.id, user.role.value, user.organization_id),
        expires_in_seconds=settings.access_token_minutes * 60,
    )


@router.post("/login", response_model=AuthLoginResponse)
def login(payload: AuthLoginRequest, db: Session = Depends(get_db)):
    email: str | None = None
    full_name = payload.full_name

    if payload.google_id_token:
        identity = verify_google_id_token(payload.google_id_token)
        email = identity.get("email")
        full_name = full_name or identity.get("name")
    elif settings.allow_insecure_dev and payload.email:
        email = payload.email

    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email identity is required")

    email = email.lower().strip()
    now = datetime.utcnow()

    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    invite = None
    if payload.invite_token:
        invite = db.execute(
            select(OrganizationInvite).where(
                OrganizationInvite.token == payload.invite_token,
                OrganizationInvite.status == InviteStatus.PENDING,
            )
        ).scalar_one_or_none()
        if not invite:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid invite token")
        if invite.expires_at < now:
            invite.status = InviteStatus.EXPIRED
            db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite token expired")
        if invite.email.lower().strip() != email:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invite email mismatch")

    if user is None:
        if invite:
            organization_id = invite.organization_id
            role = invite.role
            invite.status = InviteStatus.ACCEPTED
            invite.accepted_at = now
        else:
            org_name = (payload.organization_name or "").strip()
            if not org_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="New users must provide organization_name or valid invite_token",
                )
            org_slug = _slugify(org_name)
            if db.execute(select(Organization).where(Organization.slug == org_slug)).scalar_one_or_none():
                org_slug = f"{org_slug}-{uuid.uuid4().hex[:6]}"

            organization = Organization(name=org_name, slug=org_slug)
            db.add(organization)
            db.flush()

            organization_id = organization.id
            role = UserRole.ORG_ADMIN

        user = User(
            email=email,
            full_name=full_name,
            organization_id=organization_id,
            role=role,
            oauth_provider="google",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if invite and user.organization_id != invite.organization_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already belongs to a different organization",
            )
        if invite and user.role != invite.role:
            user.role = invite.role
            invite.status = InviteStatus.ACCEPTED
            invite.accepted_at = now
            db.commit()
            db.refresh(user)

    organization = db.get(Organization, user.organization_id)
    if not organization:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Organization not found")

    tokens = _issue_tokens(user)
    return AuthLoginResponse(tokens=tokens, user=user, organization=organization)


@router.post("/refresh", response_model=TokenPair)
def refresh_token(payload: AuthRefreshRequest, db: Session = Depends(get_db)):
    try:
        decoded = decode_token(payload.refresh_token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    if decoded.token_type != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user = db.get(User, decoded.sub)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")

    return _issue_tokens(user)
