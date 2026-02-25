from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

from ..models import AuditLog, Transaction


def transactions_to_rows(transactions: list[Transaction]) -> list[dict[str, Any]]:
    rows = []
    for tx in transactions:
        rows.append(
            {
                "transaction_id": tx.id,
                "organization_id": tx.organization_id,
                "user_id": tx.user_id,
                "upi_id": tx.upi_id,
                "sender_name": tx.sender_name,
                "receiver_name": tx.receiver_name,
                "merchant_name": tx.merchant_name,
                "merchant_category": tx.merchant_category,
                "transaction_amount": tx.transaction_amount,
                "currency": tx.currency,
                "transaction_type": tx.transaction_type.value,
                "transaction_status": tx.transaction_status.value,
                "transaction_date": str(tx.transaction_date),
                "transaction_time": str(tx.transaction_time),
                "geo_latitude": tx.geo_latitude,
                "geo_longitude": tx.geo_longitude,
                "city": tx.city,
                "state": tx.state,
                "country": tx.country,
                "ip_address": tx.ip_address,
                "device_id": tx.device_id,
                "device_type": tx.device_type,
                "risk_score": tx.risk_score,
                "is_flagged": tx.is_flagged,
                "is_frozen": tx.is_frozen,
                "notes": tx.notes,
                "tags": ", ".join(tx.tags or []),
                "created_by": tx.created_by,
                "created_at": tx.created_at.isoformat(),
            }
        )
    return rows


def audit_to_rows(logs: list[AuditLog]) -> list[dict[str, Any]]:
    rows = []
    for log in logs:
        rows.append(
            {
                "log_id": log.id,
                "organization_id": log.organization_id,
                "user_id": log.user_id,
                "action_type": log.action_type,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "timestamp": log.timestamp.isoformat(),
                "ip_address": log.ip_address,
                "details": log.details,
            }
        )
    return rows


def export_csv(rows: list[dict[str, Any]]) -> bytes:
    frame = pd.DataFrame(rows)
    return frame.to_csv(index=False).encode("utf-8")


def export_excel(rows: list[dict[str, Any]]) -> bytes:
    frame = pd.DataFrame(rows)
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="export")
    return out.getvalue()


def export_pdf(title: str, rows: list[dict[str, Any]], max_rows: int = 120) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except Exception as exc:
        raise RuntimeError("reportlab is required for PDF export") from exc

    out = BytesIO()
    pdf = canvas.Canvas(out, pagesize=A4)
    width, height = A4

    y = height - 36
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(36, y, title)

    y -= 20
    pdf.setFont("Helvetica", 8)
    for row in rows[:max_rows]:
        if y < 40:
            pdf.showPage()
            y = height - 36
            pdf.setFont("Helvetica", 8)

        text = " | ".join(f"{key}={value}" for key, value in row.items())
        pdf.drawString(36, y, text[:180])
        y -= 12

    pdf.save()
    out.seek(0)
    return out.getvalue()
