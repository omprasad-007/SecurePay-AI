from __future__ import annotations

import json
import uuid
from datetime import datetime
from io import BytesIO
from typing import Any

import pandas as pd


def _to_float(value: Any, default: float | None = 0.0) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_str(value: Any, default: str | None = "") -> str | None:
    if value is None:
        return default
    return str(value).strip()


def _parse_datetime(date_value: Any, time_value: Any = None) -> datetime | None:
    if isinstance(date_value, datetime):
        return date_value

    date_text = _to_str(date_value)
    time_text = _to_str(time_value)

    if time_text:
        combined = f"{date_text} {time_text}".strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
            try:
                return datetime.strptime(combined, fmt)
            except ValueError:
                continue

    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_text, fmt)
        except ValueError:
            continue

    return None


def _normalize_row(row: dict[str, Any], _index: int) -> dict[str, Any] | None:
    tx_id = _to_str(row.get("transaction_id") or row.get("id"))
    if not tx_id:
        tx_id = str(uuid.uuid4())
    amount = _to_float(row.get("transaction_amount") or row.get("amount"), 0.0)

    tx_dt = _parse_datetime(
        row.get("transaction_datetime") or row.get("timestamp") or row.get("transaction_date"),
        row.get("transaction_time"),
    )
    if tx_dt is None:
        return None
    if amount is None or amount <= 0:
        return None

    return {
        "transaction_id": tx_id,
        "sender_name": _to_str(row.get("sender_name") or row.get("sender"), None),
        "receiver_name": _to_str(row.get("receiver_name") or row.get("receiver"), None),
        "merchant_name": _to_str(row.get("merchant_name") or row.get("merchant"), None),
        "transaction_amount": amount,
        "currency": _to_str(row.get("currency"), None) or "INR",
        "transaction_status": _to_str(row.get("transaction_status") or row.get("status"), None),
        "transaction_datetime": tx_dt,
        "city": _to_str(row.get("city"), None),
        "state": _to_str(row.get("state"), None),
        "country": _to_str(row.get("country"), None),
        "geo_latitude": _to_float(row.get("geo_latitude") or row.get("lat"), None),
        "geo_longitude": _to_float(row.get("geo_longitude") or row.get("lon"), None),
        "device_id": _to_str(row.get("device_id"), None),
        "ip_address": _to_str(row.get("ip_address") or row.get("ip"), None),
    }


def parse_uploaded_file(file_name: str, content: bytes) -> list[dict[str, Any]]:
    lower = file_name.lower()

    if lower.endswith(".csv"):
        frame = pd.read_csv(BytesIO(content))
        rows = frame.to_dict(orient="records")
    elif lower.endswith(".xlsx"):
        frame = pd.read_excel(BytesIO(content))
        rows = frame.to_dict(orient="records")
    elif lower.endswith(".json"):
        parsed = json.loads(content.decode("utf-8"))
        if isinstance(parsed, dict):
            rows = parsed.get("transactions", []) if isinstance(parsed.get("transactions"), list) else [parsed]
        else:
            rows = parsed
    elif lower.endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except Exception as exc:
            raise ValueError("PDF parsing dependency missing. Install pypdf.") from exc

        reader = PdfReader(BytesIO(content))
        rows = []
        for page_index, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            for line_index, line in enumerate(lines):
                parts = [part.strip() for part in line.split(",")]
                if len(parts) < 3:
                    continue
                rows.append(
                    {
                        "transaction_id": f"PDF-{page_index+1}-{line_index+1}",
                        "merchant_name": parts[0],
                        "transaction_amount": parts[1],
                        "transaction_status": parts[2],
                    }
                )
    else:
        raise ValueError("Unsupported file type")

    normalized: list[dict[str, Any]] = []
    for idx, raw in enumerate(rows):
        if not isinstance(raw, dict):
            continue
        row = _normalize_row(raw, idx)
        if row is not None:
            normalized.append(row)

    return normalized
