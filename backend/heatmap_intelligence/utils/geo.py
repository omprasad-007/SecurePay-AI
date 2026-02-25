from __future__ import annotations

import math
from datetime import date, datetime


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rad = math.pi / 180.0
    dlat = (lat2 - lat1) * rad
    dlon = (lon2 - lon1) * rad
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1 * rad) * math.cos(lat2 * rad) * math.sin(dlon / 2) ** 2
    )
    return 6371 * (2 * math.asin(math.sqrt(a)))


def heat_risk_level(score: float) -> str:
    if score <= 30:
        return "Low"
    if score <= 60:
        return "Medium"
    if score <= 80:
        return "High"
    return "Critical"


def device_type_from_id(device_id: str | None) -> str:
    text = (device_id or "").lower()
    if "android" in text:
        return "Android"
    if "ios" in text or "iphone" in text:
        return "iOS"
    if "win" in text:
        return "Windows"
    if "mac" in text:
        return "macOS"
    if "web" in text or "browser" in text:
        return "Web"
    return "Unknown"


def to_datetime_bounds(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    return datetime.combine(start_date, datetime.min.time()), datetime.combine(end_date, datetime.max.time())

