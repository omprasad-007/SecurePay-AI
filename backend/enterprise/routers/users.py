from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..deps import Principal, get_client_ip, get_current_principal, get_db, require_roles
from ..models import OrganizationInvite, User, UserRole
from ..schemas import InviteUserRequest, InviteUserResponse, UserOut
from ..services.audit import write_audit_log

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/invite", response_model=InviteUserResponse)
def invite_user(
    payload: InviteUserRequest,
    request: Request,
    organization_id: str | None = Query(default=None),
    principal: Principal = Depends(require_roles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    target_org = organization_id if (principal.role == UserRole.SUPER_ADMIN and organization_id) else principal.organization_id

    existing = db.execute(select(User).where(func.lower(User.email) == payload.email.lower())).scalar_one_or_none()
    if existing and existing.organization_id != target_org:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already belongs to another organization")

    token = uuid.uuid4().hex + uuid.uuid4().hex[:8]
    invite = OrganizationInvite(
        organization_id=target_org,
        email=payload.email.lower(),
        role=payload.role,
        invited_by_user_id=principal.user_id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    write_audit_log(
        db,
        principal,
        action_type="CREATE",
        entity_type="USER_INVITE",
        entity_id=invite.id,
        ip_address=get_client_ip(request),
        details={"email": payload.email, "role": payload.role.value, "organization_id": target_org},
    )

    return InviteUserResponse(
        invite_id=invite.id,
        email=invite.email,
        role=invite.role,
        organization_id=invite.organization_id,
        invite_token=invite.token,
        expires_at=invite.expires_at,
    )


@router.get("", response_model=list[UserOut])
def list_users(
    organization_id: str | None = Query(default=None),
    principal: Principal = Depends(require_roles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN, UserRole.VIEWER, UserRole.ANALYST)),
    db: Session = Depends(get_db),
):
    target_org = organization_id if (principal.role == UserRole.SUPER_ADMIN and organization_id) else principal.organization_id

    users = db.execute(
        select(User).where(User.organization_id == target_org).order_by(User.created_at.desc())
    ).scalars().all()
    return users


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    request: Request,
    principal: Principal = Depends(require_roles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if principal.role != UserRole.SUPER_ADMIN and user.organization_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-organization access denied")

    if user.role == UserRole.SUPER_ADMIN and principal.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete SUPER_ADMIN")

    user.is_active = False
    db.commit()

    write_audit_log(
        db,
        principal,
        action_type="DELETE",
        entity_type="USER",
        entity_id=user_id,
        ip_address=get_client_ip(request),
        details={"email": user.email},
    )

    return {"status": "deleted", "user_id": user_id}
