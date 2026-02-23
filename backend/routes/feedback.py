from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from security import get_current_user

router = APIRouter(prefix="", tags=["feedback"])

FEEDBACK_PATH = Path(__file__).resolve().parents[1] / "feedback.json"


class FeedbackRequest(BaseModel):
    transaction_id: str
    label: str
    notes: Optional[str] = None
    score: Optional[float] = None


def _append_feedback(entry: dict) -> None:
    entries = []
    if FEEDBACK_PATH.exists():
        try:
            entries = json.loads(FEEDBACK_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            entries = []
    entries.append(entry)
    FEEDBACK_PATH.write_text(json.dumps(entries, indent=2), encoding="utf-8")


@router.post("/feedback")
async def submit_feedback(payload: FeedbackRequest, user=Depends(get_current_user)):
    role = (user or {}).get("role", "Analyst")
    label = payload.label.lower()
    if role not in {"Admin", "Risk Analyst"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    if label == "fraud" and role != "Risk Analyst":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Risk Analyst can mark fraud")

    entry = {
        "transaction_id": payload.transaction_id,
        "label": label,
        "notes": payload.notes,
        "score": payload.score,
        "role": role,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _append_feedback(entry)
    return {"status": "ok", "stored": entry}
