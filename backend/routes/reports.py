from __future__ import annotations

import base64
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from security import get_current_user
from generate_report import generate_csv, weekly_summary, generate_pdf_summary

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportRequest(BaseModel):
    history: List[dict] = []
    report_type: str = "csv"


@router.post("/export")
async def export_report(payload: ReportRequest, user=Depends(get_current_user)):
    role = (user or {}).get("role", "Analyst")
    if role not in {"Admin", "Auditor"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    summary = weekly_summary(payload.history)

    if payload.report_type == "metrics":
        return {"summary": summary}

    if payload.report_type == "summary_pdf":
        pdf_bytes = generate_pdf_summary(summary)
        return {"pdf_base64": base64.b64encode(pdf_bytes).decode("utf-8"), "summary": summary}

    csv_data = generate_csv(payload.history)
    return {"csv": csv_data, "summary": summary}
