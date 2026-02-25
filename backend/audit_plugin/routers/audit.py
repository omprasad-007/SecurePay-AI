from __future__ import annotations

from datetime import date
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import AuditContext, request_ip, require_roles
from ..repositories.audit_repository import (
    aggregate_metrics,
    create_report_log,
    history_rows,
    query_audit_rows,
    store_audit_rows,
)
from ..schemas import (
    AuditCompareResponse,
    AuditSummaryResponse,
    EmailReportRequest,
    EmailReportResponse,
    UploadResponse,
    UploadSummary,
)
from ..services.alert_engine import evaluate_alerts
from ..services.compare_service import build_compare
from ..services.email_service import send_report_email
from ..services.export_service import export_bytes
from ..services.risk_analysis import analyze_rows
from ..services.summary_service import build_audit_summary
from ..utils.date_math import to_datetime_bounds
from ..utils.file_parser import parse_uploaded_file
from ..utils.validators import validate_date_range, validate_upload

router = APIRouter(prefix="/api/audit", tags=["audit-advanced"])


@router.get("/export")
def export_audit_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    format: str = Query(default="csv"),
    risk_level: str | None = Query(default=None),
    transaction_status: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    ctx: AuditContext = Depends(require_roles("SUPER_ADMIN", "ORG_ADMIN", "ANALYST", "VIEWER")),
    db: Session = Depends(get_db),
):
    validate_date_range(start_date, end_date)
    start_dt, end_dt = to_datetime_bounds(start_date, end_date)

    rows = query_audit_rows(
        db=db,
        ctx=ctx,
        start_dt=start_dt,
        end_dt=end_dt,
        risk_level=risk_level,
        transaction_status=transaction_status,
        user_id=user_id,
    )

    try:
        file_bytes, media_type, extension = export_bytes(rows, format)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    filename = f"audit_export_{start_date.isoformat()}_{end_date.isoformat()}.{extension}"
    create_report_log(
        db=db,
        ctx=ctx,
        start_date=start_date,
        end_date=end_date,
        report_type="AUDIT_EXPORT",
        file_format=extension,
        file_name=filename,
        email_to=None,
        status="GENERATED",
        meta={
            "record_count": len(rows),
            "risk_level": risk_level,
            "transaction_status": transaction_status,
            "user_id": user_id,
        },
    )

    return StreamingResponse(
        BytesIO(file_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_audit_transactions(
    file: UploadFile = File(...),
    ctx: AuditContext = Depends(require_roles("SUPER_ADMIN", "ORG_ADMIN", "ANALYST")),
    db: Session = Depends(get_db),
):
    content = await file.read()
    validate_upload(file, len(content))

    try:
        parsed_rows = parse_uploaded_file(file.filename or "audit_upload", content)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not parsed_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid transactions found in uploaded file.",
        )

    history = history_rows(db, ctx)
    analyzed_rows = analyze_rows(parsed_rows, history)
    stored = store_audit_rows(db, ctx, analyzed_rows, source_file=file.filename or "audit_upload")
    metrics = aggregate_metrics(stored)

    tx_dates = [item.transaction_datetime.date() for item in stored]
    evaluate_alerts(
        db=db,
        ctx=ctx,
        overall_risk_score=float(metrics["avg_risk"]),
        high_risk_percentage=float(metrics["high_risk_pct"]),
        start_date=min(tx_dates),
        end_date=max(tx_dates),
    )

    distribution = {"Low": 0, "Medium": 0, "High": 0}
    for item in stored:
        distribution[item.risk_level] = distribution.get(item.risk_level, 0) + 1

    summary = UploadSummary(
        uploaded_records=len(parsed_rows),
        stored_records=len(stored),
        flagged_records=metrics["high_risk_count"],
        average_risk_score=metrics["avg_risk"],
        risk_level_distribution=distribution,
    )

    # Convert stored objects (which might be SQLAlchemy models) to dicts for the preview
    preview_data = []
    for item in stored[:10]:
        if hasattr(item, "__dict__"):
            d = dict(item.__dict__)
            d.pop("_sa_instance_state", None)
            preview_data.append(d)
        else:
            preview_data.append(item)

    return UploadResponse(
        success=True,
        preview=preview_data,
        totalRows=len(stored),
        summary=summary,
        message="Audit transactions analyzed and stored successfully."
    )


@router.get("/summary", response_model=AuditSummaryResponse)
def audit_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    ctx: AuditContext = Depends(require_roles("SUPER_ADMIN", "ORG_ADMIN", "ANALYST", "VIEWER")),
    db: Session = Depends(get_db),
):
    validate_date_range(start_date, end_date)
    return build_audit_summary(db, ctx, start_date, end_date)


@router.get("/compare", response_model=AuditCompareResponse)
def audit_compare(
    start_date: date = Query(...),
    end_date: date = Query(...),
    ctx: AuditContext = Depends(require_roles("SUPER_ADMIN", "ORG_ADMIN", "ANALYST", "VIEWER")),
    db: Session = Depends(get_db),
):
    validate_date_range(start_date, end_date)
    return build_compare(db, ctx, start_date, end_date)


@router.post("/email-report", response_model=EmailReportResponse)
def email_audit_report(
    payload: EmailReportRequest,
    request: Request,
    ctx: AuditContext = Depends(require_roles("SUPER_ADMIN", "ORG_ADMIN")),
    db: Session = Depends(get_db),
):
    validate_date_range(payload.start_date, payload.end_date)
    start_dt, end_dt = to_datetime_bounds(payload.start_date, payload.end_date)
    rows = query_audit_rows(db, ctx, start_dt, end_dt)

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No audit records available for the selected period.",
        )

    if not settings.smtp_host:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMTP service is not configured.",
        )

    filename = f"audit_report_{payload.start_date.isoformat()}_{payload.end_date.isoformat()}"
    try:
        send_report_email(
            smtp_host=settings.smtp_host,
            smtp_port=settings.smtp_port,
            smtp_user=settings.smtp_user,
            smtp_password=settings.smtp_password,
            smtp_sender=settings.smtp_sender,
            use_tls=settings.smtp_tls,
            recipient_email=str(payload.email),
            attachment_name=filename,
            attachment_rows=rows,
        )
        status_text = "SENT"
    except Exception as exc:
        status_text = "FAILED"
        create_report_log(
            db=db,
            ctx=ctx,
            start_date=payload.start_date,
            end_date=payload.end_date,
            report_type="EMAIL_EXPORT",
            file_format="pdf",
            file_name=f"{filename}.pdf",
            email_to=str(payload.email),
            status=status_text,
            meta={"error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send audit report email.",
        ) from exc

    report = create_report_log(
        db=db,
        ctx=ctx,
        start_date=payload.start_date,
        end_date=payload.end_date,
        report_type="EMAIL_EXPORT",
        file_format="pdf",
        file_name=f"{filename}.pdf",
        email_to=str(payload.email),
        status=status_text,
        meta={"record_count": len(rows), "request_ip": request_ip(request)},
    )
    return EmailReportResponse(status=status_text, report_id=report.id, email=payload.email)
