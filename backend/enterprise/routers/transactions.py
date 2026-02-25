from __future__ import annotations

from datetime import date, datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import Select, and_, asc, desc, func, select
from sqlalchemy.orm import Session

from ..deps import Principal, get_client_ip, get_db, require_roles
from ..models import Organization, Transaction, TransactionComment, TransactionStatus, UserRole
from ..schemas import (
    TransactionCommentCreate,
    TransactionCommentOut,
    TransactionCreate,
    TransactionListResponse,
    TransactionOut,
    TransactionUpdate,
)
from ..services.audit import write_audit_log
from ..services.exporter import export_csv, export_excel, export_pdf, transactions_to_rows
from ..services.fraud import compute_transaction_risk

router = APIRouter(prefix="/transactions", tags=["transactions"])

SORT_FIELDS = {
    "date": Transaction.transaction_date,
    "amount": Transaction.transaction_amount,
    "risk_score": Transaction.risk_score,
    "created_at": Transaction.created_at,
}


def _tenant_guard(query: Select, principal: Principal, organization_id: str | None = None) -> Select:
    if principal.role == UserRole.SUPER_ADMIN:
        if organization_id:
            return query.where(Transaction.organization_id == organization_id)
        return query
    return query.where(Transaction.organization_id == principal.organization_id)


def _apply_filters(
    query: Select,
    date_from: date | None,
    date_to: date | None,
    amount_min: float | None,
    amount_max: float | None,
    merchant: str | None,
    city: str | None,
    status_filter: TransactionStatus | None,
    risk_min: float | None,
    risk_max: float | None,
    is_flagged: bool | None,
) -> Select:
    conditions = [Transaction.deleted_at.is_(None)]

    if date_from:
        conditions.append(Transaction.transaction_date >= date_from)
    if date_to:
        conditions.append(Transaction.transaction_date <= date_to)

    if amount_min is not None:
        conditions.append(Transaction.transaction_amount >= amount_min)
    if amount_max is not None:
        conditions.append(Transaction.transaction_amount <= amount_max)

    if merchant:
        conditions.append(Transaction.merchant_name.ilike(f"%{merchant}%"))
    if city:
        conditions.append(Transaction.city.ilike(f"%{city}%"))

    if status_filter:
        conditions.append(Transaction.transaction_status == status_filter)

    if risk_min is not None:
        conditions.append(Transaction.risk_score >= risk_min)
    if risk_max is not None:
        conditions.append(Transaction.risk_score <= risk_max)

    if is_flagged is not None:
        conditions.append(Transaction.is_flagged == is_flagged)

    return query.where(and_(*conditions))


@router.post("", response_model=TransactionOut)
def create_transaction(
    payload: TransactionCreate,
    request: Request | None = None,
    principal: Principal = Depends(require_roles(UserRole.ORG_ADMIN, UserRole.ANALYST, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    organization_id = principal.organization_id
    user_id = payload.user_id or principal.user_id

    history = db.execute(
        select(Transaction)
        .where(
            Transaction.organization_id == organization_id,
            Transaction.deleted_at.is_(None),
        )
        .order_by(Transaction.created_at.desc())
        .limit(300)
    ).scalars().all()

    tx_row = {
        "id": "pending",
        "user_id": user_id,
        "upi_id": payload.upi_id,
        "transaction_amount": payload.transaction_amount,
        "device_id": payload.device_id,
        "merchant_name": payload.merchant_name,
        "transaction_type": payload.transaction_type.value,
        "ip_address": payload.ip_address,
        "city": payload.city,
        "geo_latitude": payload.geo_latitude,
        "geo_longitude": payload.geo_longitude,
        "timestamp": datetime.combine(payload.transaction_date, payload.transaction_time).isoformat() + "Z",
    }

    organization = db.get(Organization, organization_id)
    fraud_threshold = float(organization.fraud_threshold) if organization else 70.0
    risk = compute_transaction_risk(tx_row, history, fraud_threshold)

    transaction = Transaction(
        organization_id=organization_id,
        user_id=user_id,
        created_by=principal.user_id,
        upi_id=payload.upi_id,
        sender_name=payload.sender_name,
        receiver_name=payload.receiver_name,
        merchant_name=payload.merchant_name,
        merchant_category=payload.merchant_category,
        transaction_amount=payload.transaction_amount,
        currency=payload.currency,
        transaction_type=payload.transaction_type,
        transaction_status=payload.transaction_status,
        transaction_date=payload.transaction_date,
        transaction_time=payload.transaction_time,
        geo_latitude=payload.geo_latitude,
        geo_longitude=payload.geo_longitude,
        city=payload.city,
        state=payload.state,
        country=payload.country,
        ip_address=payload.ip_address,
        device_id=payload.device_id,
        device_type=payload.device_type,
        notes=payload.notes,
        tags=payload.tags,
        risk_score=risk["risk_score"],
        is_flagged=risk["is_flagged"],
        fraud_signals=risk["fraud_signals"],
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    write_audit_log(
        db,
        principal,
        action_type="CREATE",
        entity_type="TRANSACTION",
        entity_id=transaction.id,
        ip_address=get_client_ip(request),
        details={"risk_score": transaction.risk_score, "is_flagged": transaction.is_flagged},
    )

    return transaction


@router.get("", response_model=TransactionListResponse)
def get_transactions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    sort_by: str = Query(default="date"),
    sort_order: str = Query(default="desc"),
    organization_id: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    amount_min: float | None = Query(default=None),
    amount_max: float | None = Query(default=None),
    merchant: str | None = Query(default=None),
    city: str | None = Query(default=None),
    status_filter: TransactionStatus | None = Query(default=None, alias="status"),
    risk_min: float | None = Query(default=None),
    risk_max: float | None = Query(default=None),
    is_flagged: bool | None = Query(default=None),
    principal: Principal = Depends(require_roles(UserRole.ORG_ADMIN, UserRole.ANALYST, UserRole.VIEWER, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    base = select(Transaction)
    base = _tenant_guard(base, principal, organization_id)
    base = _apply_filters(base, date_from, date_to, amount_min, amount_max, merchant, city, status_filter, risk_min, risk_max, is_flagged)

    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()

    sort_column = SORT_FIELDS.get(sort_by, Transaction.transaction_date)
    direction = desc if sort_order.lower() == "desc" else asc

    items = db.execute(
        base.order_by(direction(sort_column)).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()

    return TransactionListResponse(items=items, total=int(total), page=page, page_size=page_size)


@router.put("/{transaction_id}", response_model=TransactionOut)
def update_transaction(
    transaction_id: str,
    payload: TransactionUpdate,
    request: Request | None = None,
    principal: Principal = Depends(require_roles(UserRole.ORG_ADMIN, UserRole.ANALYST, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    tx = db.get(Transaction, transaction_id)
    if not tx or tx.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    if principal.role != UserRole.SUPER_ADMIN and tx.organization_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-organization access denied")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(tx, key, value)

    history = db.execute(
        select(Transaction)
        .where(
            Transaction.organization_id == tx.organization_id,
            Transaction.id != tx.id,
            Transaction.deleted_at.is_(None),
        )
        .order_by(Transaction.created_at.desc())
        .limit(300)
    ).scalars().all()

    tx_row = {
        "id": tx.id,
        "user_id": tx.user_id,
        "upi_id": tx.upi_id,
        "transaction_amount": tx.transaction_amount,
        "device_id": tx.device_id,
        "merchant_name": tx.merchant_name,
        "transaction_type": tx.transaction_type.value,
        "ip_address": tx.ip_address,
        "city": tx.city,
        "geo_latitude": tx.geo_latitude,
        "geo_longitude": tx.geo_longitude,
        "timestamp": datetime.combine(tx.transaction_date, tx.transaction_time).isoformat() + "Z",
    }

    organization = db.get(Organization, tx.organization_id)
    fraud_threshold = float(organization.fraud_threshold) if organization else 70.0
    risk = compute_transaction_risk(tx_row, history, fraud_threshold)
    tx.risk_score = risk["risk_score"]
    tx.is_flagged = risk["is_flagged"]
    tx.fraud_signals = risk["fraud_signals"]

    if tx.is_frozen:
        tx.transaction_status = TransactionStatus.FROZEN

    db.commit()
    db.refresh(tx)

    write_audit_log(
        db,
        principal,
        action_type="EDIT",
        entity_type="TRANSACTION",
        entity_id=tx.id,
        ip_address=get_client_ip(request),
        details={"updated_fields": list(updates.keys()), "risk_score": tx.risk_score},
    )

    return tx


@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: str,
    request: Request,
    principal: Principal = Depends(require_roles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    tx = db.get(Transaction, transaction_id)
    if not tx or tx.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    if principal.role != UserRole.SUPER_ADMIN and tx.organization_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-organization access denied")

    tx.deleted_at = datetime.utcnow()
    db.commit()

    write_audit_log(
        db,
        principal,
        action_type="DELETE",
        entity_type="TRANSACTION",
        entity_id=tx.id,
        ip_address=get_client_ip(request),
        details={"soft_delete": True},
    )

    return {"status": "deleted", "transaction_id": transaction_id}


@router.get("/export")
def export_transactions(
    format: str = Query(default="csv"),
    fraud_only: bool = Query(default=False),
    organization_id: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    amount_min: float | None = Query(default=None),
    amount_max: float | None = Query(default=None),
    merchant: str | None = Query(default=None),
    city: str | None = Query(default=None),
    status_filter: TransactionStatus | None = Query(default=None, alias="status"),
    risk_min: float | None = Query(default=None),
    risk_max: float | None = Query(default=None),
    is_flagged: bool | None = Query(default=None),
    request: Request | None = None,
    principal: Principal = Depends(require_roles(UserRole.ORG_ADMIN, UserRole.ANALYST, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    base = select(Transaction)
    base = _tenant_guard(base, principal, organization_id)
    base = _apply_filters(base, date_from, date_to, amount_min, amount_max, merchant, city, status_filter, risk_min, risk_max, is_flagged)

    if fraud_only:
        base = base.where(Transaction.is_flagged.is_(True))

    txs = db.execute(base.order_by(desc(Transaction.created_at))).scalars().all()
    rows = transactions_to_rows(txs)

    fmt = format.lower().strip()
    filename = f"transactions_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    if fmt == "csv":
        content = export_csv(rows)
        media_type = "text/csv"
        extension = "csv"
    elif fmt in {"xlsx", "excel"}:
        content = export_excel(rows)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        extension = "xlsx"
    elif fmt == "pdf":
        content = export_pdf("Transactions Export", rows)
        media_type = "application/pdf"
        extension = "pdf"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported export format")

    write_audit_log(
        db,
        principal,
        action_type="DOWNLOAD",
        entity_type="TRANSACTION_EXPORT",
        entity_id=filename,
        ip_address=get_client_ip(request),
        details={"format": fmt, "fraud_only": fraud_only, "records": len(rows)},
    )

    stream = BytesIO(content)
    headers = {"Content-Disposition": f'attachment; filename="{filename}.{extension}"'}
    return StreamingResponse(stream, media_type=media_type, headers=headers)


@router.get("/{transaction_id}/report")
def export_transaction_report(
    transaction_id: str,
    request: Request,
    principal: Principal = Depends(require_roles(UserRole.ORG_ADMIN, UserRole.ANALYST, UserRole.VIEWER, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    tx = db.get(Transaction, transaction_id)
    if not tx or tx.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    if principal.role != UserRole.SUPER_ADMIN and tx.organization_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-organization access denied")

    rows = transactions_to_rows([tx])
    content = export_pdf(f"Transaction Report: {tx.id}", rows, max_rows=10)

    write_audit_log(
        db,
        principal,
        action_type="DOWNLOAD",
        entity_type="TRANSACTION_REPORT",
        entity_id=tx.id,
        ip_address=get_client_ip(request),
        details={"format": "pdf"},
    )

    stream = BytesIO(content)
    headers = {"Content-Disposition": f'attachment; filename="transaction_{tx.id}.pdf"'}
    return StreamingResponse(stream, media_type="application/pdf", headers=headers)


@router.post("/{transaction_id}/comments", response_model=TransactionCommentOut)
def add_transaction_comment(
    transaction_id: str,
    payload: TransactionCommentCreate,
    request: Request,
    principal: Principal = Depends(require_roles(UserRole.ORG_ADMIN, UserRole.ANALYST, UserRole.VIEWER, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    tx = db.get(Transaction, transaction_id)
    if not tx or tx.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    if principal.role != UserRole.SUPER_ADMIN and tx.organization_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-organization access denied")

    comment = TransactionComment(
        organization_id=tx.organization_id,
        transaction_id=tx.id,
        user_id=principal.user_id,
        comment=payload.comment,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    write_audit_log(
        db,
        principal,
        action_type="CREATE",
        entity_type="TRANSACTION_COMMENT",
        entity_id=comment.id,
        ip_address=get_client_ip(request),
        details={"transaction_id": tx.id},
    )

    return comment


@router.get("/{transaction_id}/comments", response_model=list[TransactionCommentOut])
def get_transaction_comments(
    transaction_id: str,
    principal: Principal = Depends(require_roles(UserRole.ORG_ADMIN, UserRole.ANALYST, UserRole.VIEWER, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    tx = db.get(Transaction, transaction_id)
    if not tx or tx.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    if principal.role != UserRole.SUPER_ADMIN and tx.organization_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-organization access denied")

    comments = db.execute(
        select(TransactionComment)
        .where(
            TransactionComment.transaction_id == tx.id,
            TransactionComment.organization_id == tx.organization_id,
        )
        .order_by(desc(TransactionComment.created_at))
    ).scalars().all()

    return comments
