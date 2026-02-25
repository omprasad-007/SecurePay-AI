from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import Principal, get_db, get_current_principal, require_roles
from ..models import Organization, UserRole
from ..schemas import FraudThresholdUpdate, OrganizationCreateRequest, OrganizationOut
from ..services.audit import write_audit_log

router = APIRouter(prefix="/organization", tags=["organization"])


@router.post("", response_model=OrganizationOut)
def create_organization(
    payload: OrganizationCreateRequest,
    principal: Principal = Depends(require_roles(UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    exists = db.execute(select(Organization).where(Organization.slug == payload.slug)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization slug already exists")

    org = Organization(name=payload.name, slug=payload.slug, fraud_threshold=payload.fraud_threshold)
    db.add(org)
    db.commit()
    db.refresh(org)

    write_audit_log(
        db,
        principal,
        action_type="CREATE",
        entity_type="ORG",
        entity_id=org.id,
        ip_address="system",
        details={"name": payload.name, "slug": payload.slug},
    )

    return org


@router.get("", response_model=OrganizationOut | list[OrganizationOut])
def get_organization(
    all_orgs: bool = Query(default=False),
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    if all_orgs:
        if principal.role != UserRole.SUPER_ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only SUPER_ADMIN can list all orgs")
        return db.execute(select(Organization).order_by(Organization.created_at.desc())).scalars().all()

    org = db.get(Organization, principal.organization_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


@router.patch("", response_model=OrganizationOut)
def update_fraud_threshold(
    payload: FraudThresholdUpdate,
    organization_id: str | None = Query(default=None),
    principal: Principal = Depends(require_roles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    target_org = organization_id if (principal.role == UserRole.SUPER_ADMIN and organization_id) else principal.organization_id
    org = db.get(Organization, target_org)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    org.fraud_threshold = payload.fraud_threshold
    db.commit()
    db.refresh(org)

    write_audit_log(
        db,
        principal,
        action_type="EDIT",
        entity_type="ORG",
        entity_id=org.id,
        ip_address="system",
        details={"fraud_threshold": payload.fraud_threshold},
    )

    return org
