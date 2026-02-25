from __future__ import annotations

import math
from datetime import datetime

from ..models import AuditAdvanced


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


def _risk_level(score: float) -> str:
    if score <= 30:
        return "Low"
    if score <= 60:
        return "Medium"
    return "High"


def _mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return mean, math.sqrt(variance)


def analyze_rows(rows: list[dict], history_rows: list[AuditAdvanced]) -> list[dict]:
    historical_amounts = [float(item.transaction_amount or 0.0) for item in history_rows if float(item.transaction_amount or 0.0) > 0]
    mean_amount, std_amount = _mean_std(historical_amounts)

    known_devices = {item.device_id for item in history_rows if item.device_id}
    latest_location = None
    if history_rows:
        latest = max(history_rows, key=lambda item: item.transaction_datetime)
        if latest.geo_latitude is not None and latest.geo_longitude is not None:
            latest_location = (float(latest.geo_latitude), float(latest.geo_longitude))

    enriched = []
    for row in rows:
        reasons: list[str] = []
        score = 5.0

        amount = float(row.get("transaction_amount") or 0.0)
        tx_dt: datetime = row.get("transaction_datetime") or datetime.utcnow()

        if mean_amount > 0 and amount >= mean_amount * 2:
            reasons.append("Abnormal amount")
            score += 35
        elif mean_amount > 0 and amount >= mean_amount * 1.5:
            reasons.append("Elevated amount")
            score += 20

        if std_amount > 0 and abs(amount - mean_amount) / std_amount >= 2.5:
            if "Abnormal amount" not in reasons:
                reasons.append("Abnormal amount")
            score += 15

        if tx_dt.hour in {0, 1, 2, 3, 4}:
            reasons.append("Unusual time")
            score += 20

        device_id = row.get("device_id")
        if device_id and known_devices and device_id not in known_devices:
            reasons.append("Device mismatch")
            score += 20

        lat = row.get("geo_latitude")
        lon = row.get("geo_longitude")
        if latest_location and lat is not None and lon is not None:
            distance = _haversine(latest_location[0], latest_location[1], float(lat), float(lon))
            if distance > 500:
                reasons.append("Geo anomaly")
                score += 20

        if not reasons:
            reasons.append("No critical anomaly")

        score = max(0.0, min(100.0, score))
        row["risk_score"] = round(score, 2)
        row["risk_level"] = _risk_level(score)
        row["risk_reasons"] = reasons
        enriched.append(row)

    return enriched
