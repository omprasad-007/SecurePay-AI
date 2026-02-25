from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

from models.adaptive_risk import adaptive_risk
from models.fraud_pipeline import score_transaction

from ..models import Transaction


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rad = math.pi / 180
    dlat = (lat2 - lat1) * rad
    dlon = (lon2 - lon1) * rad
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1 * rad) * math.cos(lat2 * rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    return 6371 * c


def _legacy_timestamp(transaction_date, transaction_time) -> str:
    dt = datetime.combine(transaction_date, transaction_time).replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _to_legacy_tx(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "userId": row["user_id"],
        "receiverId": row.get("receiver_id") or row.get("upi_id") or "RECEIVER",
        "amount": float(row["transaction_amount"]),
        "deviceId": row.get("device_id") or "",
        "merchant": row.get("merchant_name") or "Unknown",
        "channel": row.get("transaction_type", "UPI"),
        "ip": row.get("ip_address") or "0.0.0.0",
        "location": {
            "city": row.get("city") or "Unknown",
            "lat": float(row.get("geo_latitude") or 0.0),
            "lon": float(row.get("geo_longitude") or 0.0),
        },
        "timestamp": row["timestamp"],
    }


def _history_to_legacy(rows: list[Transaction]) -> list[dict[str, Any]]:
    payload = []
    for item in rows:
        payload.append(
            {
                "id": item.id,
                "user_id": item.user_id,
                "upi_id": item.upi_id,
                "transaction_amount": item.transaction_amount,
                "device_id": item.device_id,
                "merchant_name": item.merchant_name,
                "transaction_type": item.transaction_type.value,
                "ip_address": item.ip_address,
                "city": item.city,
                "geo_latitude": item.geo_latitude,
                "geo_longitude": item.geo_longitude,
                "timestamp": _legacy_timestamp(item.transaction_date, item.transaction_time),
            }
        )
    return [_to_legacy_tx(item) for item in payload]


def compute_transaction_risk(
    transaction_payload: dict[str, Any],
    history_rows: list[Transaction],
    fraud_threshold: float,
) -> dict[str, Any]:
    legacy_history = _history_to_legacy(history_rows)
    legacy_tx = _to_legacy_tx(transaction_payload)

    base = score_transaction(legacy_tx, legacy_history)
    adaptive = adaptive_risk(base, legacy_tx, legacy_history)

    risk_score = float(adaptive["adaptive_score"])
    is_flagged = risk_score >= fraud_threshold

    signals: list[str] = []

    merchant_hits = [tx for tx in history_rows if tx.merchant_name == transaction_payload["merchant_name"]]
    if len(merchant_hits) >= 3:
        signals.append("Repeated merchant risk pattern")

    current_ts = _parse_timestamp(legacy_tx["timestamp"])
    recent = [
        tx
        for tx in legacy_history
        if current_ts - timedelta(minutes=10) <= _parse_timestamp(tx.get("timestamp", "")) <= current_ts
    ]
    if len(recent) >= 3:
        signals.append("Suspicious velocity detected")

    if history_rows:
        latest = max(history_rows, key=lambda row: _legacy_timestamp(row.transaction_date, row.transaction_time))
        if (
            latest.geo_latitude is not None
            and latest.geo_longitude is not None
            and transaction_payload.get("geo_latitude") is not None
            and transaction_payload.get("geo_longitude") is not None
        ):
            distance_km = _haversine(
                float(latest.geo_latitude),
                float(latest.geo_longitude),
                float(transaction_payload["geo_latitude"]),
                float(transaction_payload["geo_longitude"]),
            )
            if distance_km > 500:
                signals.append("Geo-distance anomaly")

        known_devices = {row.device_id for row in history_rows if row.device_id}
        if transaction_payload.get("device_id") and transaction_payload["device_id"] not in known_devices:
            signals.append("Device fingerprint anomaly")

    if float(base.get("graph_risk", 0.0)) >= 50:
        signals.append("Graph relationship anomaly")

    return {
        "risk_score": round(risk_score, 2),
        "is_flagged": is_flagged,
        "fraud_signals": signals,
    }
