from __future__ import annotations

from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import Select, and_, desc, func, select
from sqlalchemy.orm import Session

from ..deps import Principal, get_client_ip, get_db, require_roles
from ..models import AuditLog, UserRole
from ..schemas import AuditListResponse
from ..services.audit import write_audit_log
from ..services.exporter import audit_to_rows, export_csv, export_excel, export_pdf

router = APIRouter(prefix="/audit", tags=["audit"])


def _audit_tenant_guard(query: Select, principal: Principal, organization_id: str | None = None) -> Select:
    if principal.role == UserRole.SUPER_ADMIN:
        if organization_id:
            return query.where(AuditLog.organization_id == organization_id)
        return query
    return query.where(AuditLog.organization_id == principal.organization_id)


def _apply_audit_filters(
    query: Select,
    user_id: str | None,
    action_type: str | None,
    entity_type: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> Select:
    conditions = []
    if user_id:
        conditions.append(AuditLog.user_id == user_id)
    if action_type:
        conditions.append(AuditLog.action_type == action_type)
    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)
    if date_from:
        conditions.append(AuditLog.timestamp >= date_from)
    if date_to:
        conditions.append(AuditLog.timestamp <= date_to)

    if conditions:
        query = query.where(and_(*conditions))
    return query


@router.get("", response_model=AuditListResponse)
def get_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    organization_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    action_type: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    principal: Principal = Depends(require_roles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    base = select(AuditLog)
    base = _audit_tenant_guard(base, principal, organization_id)
    base = _apply_audit_filters(base, user_id, action_type, entity_type, date_from, date_to)

    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    items = db.execute(
        base.order_by(desc(AuditLog.timestamp)).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()

    return AuditListResponse(items=items, total=int(total), page=page, page_size=page_size)


@router.get("/export")
def export_audit_logs(
    format: str = Query(default="csv"),
    organization_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    action_type: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    request: Request | None = None,
    principal: Principal = Depends(require_roles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    base = select(AuditLog)
    base = _audit_tenant_guard(base, principal, organization_id)
    base = _apply_audit_filters(base, user_id, action_type, entity_type, date_from, date_to)

    logs = db.execute(base.order_by(desc(AuditLog.timestamp))).scalars().all()
    rows = audit_to_rows(logs)

    fmt = format.lower().strip()
    filename = f"audit_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    if fmt == "csv":
        content = export_csv(rows)
        media_type = "text/csv"
        extension = "csv"
    elif fmt in {"xlsx", "excel"}:
        content = export_excel(rows)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        extension = "xlsx"
    elif fmt == "pdf":
        content = export_pdf("Audit Logs Export", rows)
        media_type = "application/pdf"
        extension = "pdf"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported export format")

    write_audit_log(
        db,
        principal,
        action_type="DOWNLOAD",
        entity_type="AUDIT_EXPORT",
        entity_id=filename,
        ip_address=get_client_ip(request),
        details={"format": fmt, "records": len(rows)},
    )

    stream = BytesIO(content)
    headers = {"Content-Disposition": f'attachment; filename="{filename}.{extension}"'}
    return StreamingResponse(stream, media_type=media_type, headers=headers)
