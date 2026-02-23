from __future__ import annotations

import base64
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from models.adaptive_risk import adaptive_risk
from models.decision_engine import decision_from_score
from models.fraud_pipeline import score_transaction
from models.pattern_detector import detect_patterns
from security import get_current_user
from utils.documentation_generator import generate_markdown_report
from utils.data_cleaner import clean_and_validate
from utils.excel_ingestion import detect_and_map_columns, read_excel_or_csv

router = APIRouter(prefix="", tags=["excel"])

UPLOAD_LIMIT_BYTES = 5 * 1024 * 1024
UPLOAD_RATE_LIMIT_PER_MIN = 8
upload_hits: dict[str, deque] = defaultdict(deque)

CITY_COORDS = {
    "mumbai": {"city": "Mumbai", "lat": 19.076, "lon": 72.8777},
    "delhi": {"city": "Delhi", "lat": 28.7041, "lon": 77.1025},
    "bengaluru": {"city": "Bengaluru", "lat": 12.9716, "lon": 77.5946},
    "hyderabad": {"city": "Hyderabad", "lat": 17.385, "lon": 78.4867},
    "chennai": {"city": "Chennai", "lat": 13.0827, "lon": 80.2707},
}


class ExcelUploadRequest(BaseModel):
    filename: str
    content_base64: str
    history: list[dict] = []


class ReportRequest(BaseModel):
    summary: dict
    insights: dict
    patterns: list[str] = []


def _validate_file(filename: str, content: bytes) -> None:
    lower = (filename or "").lower()
    allowed_ext = lower.endswith(".csv") or lower.endswith(".xlsx")
    if not allowed_ext:
        raise HTTPException(status_code=400, detail="Only .csv and .xlsx files are supported")

    forbidden = [".exe", ".bat", ".cmd", ".sh", ".ps1"]
    if any(lower.endswith(ext) for ext in forbidden):
        raise HTTPException(status_code=400, detail="Executable files are not allowed")

    if len(content) > UPLOAD_LIMIT_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 5MB limit")



def _check_upload_rate_limit(client_key: str) -> None:
    now = datetime.now(timezone.utc).timestamp()
    hits = upload_hits[client_key]
    while hits and now - hits[0] > 60:
        hits.popleft()
    if len(hits) >= UPLOAD_RATE_LIMIT_PER_MIN:
        raise HTTPException(status_code=429, detail="Upload rate limit exceeded")
    hits.append(now)



def _location_from_value(raw: Any) -> dict:
    if raw is None:
        return CITY_COORDS["mumbai"]
    key = str(raw).strip().lower()
    return CITY_COORDS.get(key, {"city": str(raw), "lat": 20.5937, "lon": 78.9629})



def _row_to_transaction(row: dict, index: int) -> dict:
    merchant = str(row.get("merchant") or "UnknownMerchant")
    receiver = f"MERCH{merchant[:6].upper()}"
    location = _location_from_value(row.get("location"))
    timestamp = row.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "id": str(row.get("transaction_id") or f"TXNUP{index:06d}"),
        "userId": str(row.get("user_id") or f"USER{index % 1000}"),
        "receiverId": receiver,
        "amount": float(row.get("amount") or 0),
        "deviceId": str(row.get("device_id") or f"DEV-UP-{index % 99}"),
        "merchant": merchant,
        "channel": "UPI",
        "ip": f"192.168.10.{(index % 240) + 10}",
        "location": location,
        "timestamp": timestamp,
    }



def _analytics_summary(processed: list[dict]) -> dict:
    total = len(processed)
    high = [item for item in processed if item.get("risk_level") in {"HIGH", "CRITICAL"}]
    fraud_percentage = round((len(high) / total) * 100, 2) if total else 0
    average_amount = round(sum(item.get("amount", 0) for item in processed) / total, 2) if total else 0

    merchant_scores = Counter()
    fraud_hours = Counter()
    for item in processed:
        merchant_scores[item.get("merchant", "Unknown")] += item.get("fraud_score", 0)
        if item.get("risk_level") in {"HIGH", "CRITICAL"}:
            hour = item.get("timestamp", "00:00")
            fraud_hours[str(hour)[11:13] if len(str(hour)) >= 13 else "00"] += 1

    most_risky_merchant = merchant_scores.most_common(1)[0][0] if merchant_scores else "N/A"
    peak_hour = fraud_hours.most_common(1)[0][0] if fraud_hours else "N/A"

    return {
        "total_transactions": total,
        "fraud_percentage": fraud_percentage,
        "high_risk_count": len(high),
        "average_amount": average_amount,
        "most_risky_merchant": most_risky_merchant,
        "peak_fraud_hour": peak_hour,
    }



def _dataset_insights(processed: list[dict]) -> dict:
    users = {item.get("userId") for item in processed}
    merchants = [item.get("merchant") for item in processed]
    devices = [item.get("deviceId") for item in processed]

    user_risk = Counter()
    merchant_risk = Counter()
    device_risk = Counter()

    for item in processed:
        risk = item.get("fraud_score", 0)
        user_risk[item.get("userId")] += risk
        merchant_risk[item.get("merchant")] += risk
        device_risk[item.get("deviceId")] += risk

    return {
        "unique_users": len(users),
        "total_volume": round(sum(item.get("amount", 0) for item in processed), 2),
        "merchant_categories": len(set(merchants)),
        "fraud_detection_rate": round(
            (sum(1 for item in processed if item.get("risk_level") in {"HIGH", "CRITICAL"}) / max(len(processed), 1)) * 100,
            2,
        ),
        "top_risky_users": [{"id": key, "score": round(value, 2)} for key, value in user_risk.most_common(5)],
        "top_risky_merchants": [{"id": key, "score": round(value, 2)} for key, value in merchant_risk.most_common(5)],
        "top_risky_devices": [{"id": key, "score": round(value, 2)} for key, value in device_risk.most_common(5)],
    }



def _pattern_summary(processed: list[dict]) -> list[str]:
    patterns: set[str] = set()
    for item in processed:
        for p in item.get("patterns", []):
            patterns.add(p)

    micro = [item for item in processed if item.get("amount", 0) < 200]
    if len(micro) > 10:
        patterns.add("Smurfing")

    by_user_hour = defaultdict(int)
    for item in processed:
        key = (item.get("userId"), str(item.get("timestamp", ""))[:13])
        by_user_hour[key] += 1
    if any(count >= 6 for count in by_user_hour.values()):
        patterns.add("Velocity Fraud")

    return sorted(patterns)


@router.post("/upload-excel")
async def upload_excel(payload: ExcelUploadRequest, request: Request, user=Depends(get_current_user)):
    role = (user or {}).get("role", "Risk Analyst")
    if role not in {"Admin", "Risk Analyst", "Auditor"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    client_key = request.client.host if request.client else "unknown"
    _check_upload_rate_limit(client_key)

    try:
        content = base64.b64decode(payload.content_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file encoding")

    _validate_file(payload.filename, content)

    try:
        raw_df = read_excel_or_csv(content, payload.filename)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to parse file: {exc}")

    mapped_df, mapping, missing = detect_and_map_columns(raw_df)
    cleaned_df, invalid_rows, cleaning_stats = clean_and_validate(mapped_df)

    history = payload.history or []
    processed: list[dict] = []
    working_history = list(history)

    records = cleaned_df.to_dict(orient="records")
    for index, row in enumerate(records):
        tx = _row_to_transaction(row, index)
        base = score_transaction(tx, working_history)
        adaptive = adaptive_risk(base, tx, working_history)
        decision = decision_from_score(adaptive["adaptive_score"])
        patterns = detect_patterns(tx, working_history)

        enriched = {
            **tx,
            "fraud_score": round(adaptive["adaptive_score"] / 100, 4),
            "risk_level": decision["risk_level"],
            "risk_drivers": adaptive["risk_drivers"],
            "decision_action": decision["action"],
            "patterns": patterns,
            "finalScore": round(adaptive["adaptive_score"], 2),
            "riskLevel": decision["risk_level"],
        }
        processed.append(enriched)
        working_history.append(enriched)

    summary = _analytics_summary(processed)
    insights = _dataset_insights(processed)
    patterns = _pattern_summary(processed)

    return {
        "transactions": processed,
        "analytics_summary": summary,
        "dataset_insights": insights,
        "detected_patterns": patterns,
        "column_mapping": mapping,
        "missing_columns": missing,
        "cleaning": cleaning_stats,
        "invalid_rows_count": len(invalid_rows),
    }


@router.post("/upload-excel/report")
async def generate_excel_report(payload: ReportRequest, user=Depends(get_current_user)):
    role = (user or {}).get("role", "Risk Analyst")
    if role not in {"Admin", "Auditor", "Risk Analyst"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    markdown = generate_markdown_report(payload.summary, payload.insights, payload.patterns)
    return {"report_markdown": markdown}
