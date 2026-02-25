from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..deps import Principal, get_client_ip, get_db, require_roles
from ..models import ApiKey, UserRole
from ..security import hash_api_key
from ..services.audit import write_audit_log

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post("/api-keys")
def create_api_key(
    name: str,
    request: Request,
    principal: Principal = Depends(require_roles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    raw = secrets.token_urlsafe(40)
    key_hash = hash_api_key(raw)

    api_key = ApiKey(
        organization_id=principal.organization_id,
        created_by=principal.user_id,
        name=name,
        key_hash=key_hash,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    write_audit_log(
        db,
        principal,
        action_type="CREATE",
        entity_type="API_KEY",
        entity_id=api_key.id,
        ip_address=get_client_ip(request),
        details={"name": name},
    )

    return {
        "id": api_key.id,
        "name": api_key.name,
        "organization_id": api_key.organization_id,
        "raw_api_key": raw,
        "warning": "Store this key now. It is not returned again.",
    }


@router.get("/api-keys")
def list_api_keys(
    principal: Principal = Depends(require_roles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(ApiKey)
        .where(ApiKey.organization_id == principal.organization_id)
        .order_by(desc(ApiKey.created_at))
    ).scalars().all()

    return [
        {
            "id": item.id,
            "name": item.name,
            "is_active": item.is_active,
            "created_at": item.created_at,
            "last_used_at": item.last_used_at,
        }
        for item in rows
    ]


@router.delete("/api-keys/{key_id}")
def revoke_api_key(
    key_id: str,
    request: Request,
    principal: Principal = Depends(require_roles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    key = db.get(ApiKey, key_id)
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    if principal.role != UserRole.SUPER_ADMIN and key.organization_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-organization access denied")

    key.is_active = False
    db.commit()

    write_audit_log(
        db,
        principal,
        action_type="DELETE",
        entity_type="API_KEY",
        entity_id=key.id,
        ip_address=get_client_ip(request),
        details={"name": key.name},
    )

    return {"status": "revoked", "key_id": key.id}
