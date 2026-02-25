from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import pandas as pd

from ..models import AuditAdvanced


def rows_to_dict(rows: list[AuditAdvanced]) -> list[dict[str, Any]]:
    data = []
    for row in rows:
        data.append(
            {
                "transaction_id": row.transaction_id,
                "user_id": row.user_id,
                "merchant_name": row.merchant_name,
                "transaction_amount": row.transaction_amount,
                "currency": row.currency,
                "transaction_status": row.transaction_status,
                "risk_score": row.risk_score,
                "risk_level": row.risk_level,
                "risk_reasons": row.risk_reasons,
                "transaction_datetime": row.transaction_datetime.isoformat(),
                "city": row.city,
                "state": row.state,
                "country": row.country,
                "ip_address": row.ip_address,
                "device_id": row.device_id,
            }
        )
    return data


def export_bytes(rows: list[AuditAdvanced], format_name: str) -> tuple[bytes, str, str]:
    data = rows_to_dict(rows)
    fmt = format_name.lower().strip()

    if fmt == "csv":
        frame = pd.DataFrame(data)
        return frame.to_csv(index=False).encode("utf-8"), "text/csv", "csv"

    if fmt in {"xlsx", "excel"}:
        frame = pd.DataFrame(data)
        out = BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            frame.to_excel(writer, index=False, sheet_name="audit")
        return out.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"

    if fmt == "json":
        return json.dumps(data, indent=2).encode("utf-8"), "application/json", "json"

    if fmt == "pdf":
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
        pdf.drawString(36, y, "Audit Advanced Export")
        y -= 16
        pdf.setFont("Helvetica", 8)
        for row in data[:140]:
            if y < 40:
                pdf.showPage()
                y = height - 36
                pdf.setFont("Helvetica", 8)
            line = f"{row['transaction_id']} | {row['merchant_name']} | {row['transaction_amount']} | {row['risk_score']} | {row['risk_level']}"
            pdf.drawString(36, y, line[:180])
            y -= 12
        pdf.save()
        out.seek(0)
        return out.getvalue(), "application/pdf", "pdf"

    raise ValueError("Unsupported format")
