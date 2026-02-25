from __future__ import annotations

import math
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

FACTOR_WEIGHTS: Dict[str, float] = {
    "amount_deviation_risk": 0.30,
    "location_anomaly_risk": 0.20,
    "velocity_risk": 0.15,
    "merchant_novelty_risk": 0.15,
    "time_based_risk": 0.05,
    "account_risk": 0.10,
    "graph_network_risk": 0.05,
}

FACTOR_LABELS: Dict[str, str] = {
    "amount_deviation_risk": "Amount Deviation Risk",
    "location_anomaly_risk": "Location Anomaly Risk",
    "velocity_risk": "Velocity Risk",
    "merchant_novelty_risk": "Merchant Novelty Risk",
    "time_based_risk": "Time-Based Risk",
    "account_risk": "Account Risk",
    "graph_network_risk": "Graph / Network Risk",
}

PARAMETER_NAMES: Dict[str, str] = {
    "amount_deviation_risk": "Amount Deviation",
    "location_anomaly_risk": "Location Anomaly",
    "velocity_risk": "Velocity Risk",
    "merchant_novelty_risk": "Merchant Novelty",
    "time_based_risk": "Time-Based Risk",
    "account_risk": "Account Risk",
    "graph_network_risk": "Graph / Network Risk",
}


def _parse_time(ts: str | None) -> datetime:
    if not ts:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _clamp(value: float, min_value: float = 0.0, max_value: float = 100.0) -> float:
    return max(min_value, min(max_value, value))


def _user_history(history: List[dict], user_id: str) -> List[dict]:
    return [item for item in (history or []) if item.get("userId") == user_id]


def _amount_stats(user_history: List[dict]) -> tuple[float, float]:
    amounts = [_to_float(item.get("amount"), 0.0) for item in user_history]
    amounts = [amount for amount in amounts if amount > 0]
    if not amounts:
        return 0.0, 0.0
    mean = sum(amounts) / len(amounts)
    variance = sum((amount - mean) ** 2 for amount in amounts) / len(amounts)
    return float(mean), float(math.sqrt(variance))


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


def _is_flagged_tx(item: dict) -> bool:
    label = str(item.get("riskLevel") or item.get("risk_level") or "").upper()
    score = _to_float(item.get("finalScore") or item.get("final_score"), 0.0)
    return label in {"HIGH", "CRITICAL"} or score >= 80


def _last_user_transaction(user_history: List[dict]) -> dict | None:
    if not user_history:
        return None
    return max(user_history, key=lambda item: _parse_time(item.get("timestamp")))


def _hour_distance(hour_a: int, hour_b: int) -> int:
    direct = abs(hour_a - hour_b)
    return min(direct, 24 - direct)


def _amount_deviation_risk(current_amount: float, user_history: List[dict]) -> float:
    average, std_dev = _amount_stats(user_history)
    if average <= 0:
        return 10.0

    ratio = current_amount / average if average else 1.0
    if ratio >= 5:
        score = 95 + min(5.0, (ratio - 5) * 2.0)
    elif ratio >= 3:
        score = 80.0
    elif ratio >= 2:
        score = 60.0
    elif ratio >= 1.5:
        score = 30.0
    else:
        score = 10.0

    if std_dev > 0:
        z_score = abs(current_amount - average) / (std_dev + 1e-3)
        if z_score >= 4:
            score = max(score, 95.0)
        elif z_score >= 3:
            score = max(score, 80.0)
        elif z_score >= 2:
            score = max(score, 60.0)

    return _clamp(score)


def _location_anomaly_risk(tx: dict, user_history: List[dict]) -> float:
    location = tx.get("location") if isinstance(tx.get("location"), dict) else {}
    city = str(location.get("city") or "").strip().lower()
    country = str(location.get("country") or "").strip().lower()

    if not user_history:
        base_score = 40.0
    else:
        city_counts = Counter(
            str(item.get("location", {}).get("city") or "").strip().lower()
            for item in user_history
            if item.get("location")
        )
        city_counts.pop("", None)
        total_city_events = sum(city_counts.values())

        seen_countries = {
            str(item.get("location", {}).get("country") or "").strip().lower()
            for item in user_history
            if item.get("location")
        }
        seen_countries.discard("")

        if country and seen_countries and country not in seen_countries:
            base_score = 92.0
        elif city and city in city_counts:
            frequency = city_counts[city] / max(total_city_events, 1)
            base_score = 10.0 if frequency >= 0.20 else 40.0
        elif city and total_city_events > 0:
            base_score = 70.0
        else:
            base_score = 40.0

    last_tx = _last_user_transaction(user_history)
    if last_tx and last_tx.get("location") and location:
        prev_location = last_tx.get("location", {})
        if all(key in prev_location for key in ("lat", "lon")) and all(key in location for key in ("lat", "lon")):
            distance_km = _haversine(
                _to_float(prev_location.get("lat"), 0.0),
                _to_float(prev_location.get("lon"), 0.0),
                _to_float(location.get("lat"), 0.0),
                _to_float(location.get("lon"), 0.0),
            )
            if distance_km > 1000:
                current_time = _parse_time(tx.get("timestamp"))
                last_time = _parse_time(last_tx.get("timestamp"))
                hours_between = abs((current_time - last_time).total_seconds()) / 3600
                if hours_between <= 6:
                    base_score += 15.0

    return _clamp(base_score)


def _velocity_risk(tx: dict, user_history: List[dict]) -> float:
    current_time = _parse_time(tx.get("timestamp"))
    cutoff = current_time - timedelta(minutes=10)
    recent_count = sum(
        1 for item in user_history if cutoff <= _parse_time(item.get("timestamp")) <= current_time
    )

    burst_count = recent_count + 1
    if burst_count >= 6:
        score = 90.0
    elif burst_count >= 4:
        score = 70.0
    elif burst_count >= 2:
        score = 40.0
    else:
        score = 5.0

    if user_history:
        timestamps = [_parse_time(item.get("timestamp")) for item in user_history]
        oldest = min(timestamps)
        span_minutes = max(10.0, abs((current_time - oldest).total_seconds()) / 60)
        historical_avg_10m = (len(user_history) * 10.0) / span_minutes
        if burst_count >= max(2.0, historical_avg_10m * 3.0):
            score += 10.0

    return _clamp(score)


def _merchant_novelty_risk(tx: dict, history: List[dict], user_history: List[dict], features: Dict[str, Any]) -> float:
    merchant = str(tx.get("merchant") or "").strip().lower()
    if not merchant:
        return 70.0

    user_merchant_counts = Counter(
        str(item.get("merchant") or "").strip().lower() for item in user_history
    )
    merchant_usage_count = user_merchant_counts.get(merchant, 0)

    linked_to_flagged = any(
        str(item.get("merchant") or "").strip().lower() == merchant and _is_flagged_tx(item)
        for item in history
    )

    if linked_to_flagged or _to_int(features.get("merchant_risk"), 0) == 1:
        return 90.0
    if merchant_usage_count >= 2:
        return 5.0
    if merchant_usage_count == 1:
        return 40.0
    return 70.0


def _time_based_risk(tx: dict, user_history: List[dict]) -> float:
    hour = _parse_time(tx.get("timestamp")).hour
    if 1 <= hour <= 4:
        return 80.0

    hours = [_parse_time(item.get("timestamp")).hour for item in user_history]
    if not hours:
        return 30.0

    counts = Counter(hours)
    min_count = max(2, math.ceil(len(hours) * 0.15))
    normal_hours = {hour_value for hour_value, count in counts.items() if count >= min_count}
    if not normal_hours:
        normal_hours = {hour_value for hour_value, _ in counts.most_common(min(4, len(counts)))}

    if hour in normal_hours:
        return 5.0
    if any(_hour_distance(hour, normal_hour) <= 1 for normal_hour in normal_hours):
        return 30.0
    return 30.0


def _account_risk(tx: dict, user_history: List[dict], device_context: dict | None = None) -> float:
    context = device_context or {}
    device_id = str(tx.get("deviceId") or "").strip()
    seen_devices = {str(item.get("deviceId") or "").strip() for item in user_history if item.get("deviceId")}

    inferred_new_device = bool(device_id and seen_devices and device_id not in seen_devices)
    new_device = _to_bool(context.get("newDevice")) if "newDevice" in context else inferred_new_device

    recent_password_change = _to_bool(
        context.get("recentPasswordChange")
        or context.get("passwordChangedRecently")
        or context.get("password_change_recent")
    )
    failed_logins = max(
        _to_int(context.get("failedLoginAttempts"), 0),
        _to_int(context.get("failed_logins"), 0),
        _to_int(context.get("failedAttempts"), 0),
    )
    ip_risk = _to_float(context.get("ipRisk"), 0.0)
    risky_ip = ip_risk >= 0.7

    anomaly_count = sum(
        1 for condition in (new_device, recent_password_change, failed_logins >= 3, risky_ip) if condition
    )

    if anomaly_count >= 2:
        return 90.0
    if failed_logins >= 3:
        return 70.0
    if new_device or recent_password_change or risky_ip:
        return 50.0
    return 5.0


def _graph_network_risk(tx: dict, history: List[dict], base_results: Dict[str, Any]) -> float:
    graph_score = _to_float(base_results.get("graph_risk"), 0.0)
    merchant = str(tx.get("merchant") or "").strip().lower()

    linked_flagged_count = sum(
        1
        for item in history
        if str(item.get("merchant") or "").strip().lower() == merchant and _is_flagged_tx(item)
    )

    if graph_score >= 60 or linked_flagged_count >= 3:
        score = 80.0
    elif graph_score >= 35 or linked_flagged_count >= 1:
        score = 40.0
    else:
        score = 5.0

    if score >= 80 and (graph_score >= 85 or linked_flagged_count >= 5):
        score = 90.0

    return _clamp(score)


def _risk_level_from_score(score: float) -> str:
    if score <= 30:
        return "LOW"
    if score <= 60:
        return "MEDIUM"
    if score <= 80:
        return "HIGH"
    return "CRITICAL"


def _adaptive_threshold() -> float:
    configured = _to_float(os.getenv("ADAPTIVE_ALERT_THRESHOLD", "61"), 61.0)
    return _clamp(configured)


def adaptive_risk(
    base_results: Dict[str, Any],
    tx: dict,
    history: List[dict],
    device_context: dict | None = None,
) -> Dict[str, Any]:
    history = history or []
    user_id = str(tx.get("userId") or "")
    user_history = _user_history(history, user_id)
    features = base_results.get("features", {})

    factor_scores: Dict[str, float] = {
        "amount_deviation_risk": _amount_deviation_risk(_to_float(tx.get("amount"), 0.0), user_history),
        "location_anomaly_risk": _location_anomaly_risk(tx, user_history),
        "velocity_risk": _velocity_risk(tx, user_history),
        "merchant_novelty_risk": _merchant_novelty_risk(tx, history, user_history, features),
        "time_based_risk": _time_based_risk(tx, user_history),
        "account_risk": _account_risk(tx, user_history, device_context),
        "graph_network_risk": _graph_network_risk(tx, history, base_results),
    }

    adaptive_score = _clamp(
        sum(factor_scores[factor_name] * weight for factor_name, weight in FACTOR_WEIGHTS.items())
    )

    risk_drivers = [
        {
            "factor": FACTOR_LABELS[factor_name],
            "impact": round((factor_scores[factor_name] * weight) / 100, 4),
            "score": round(factor_scores[factor_name], 2),
            "weight": weight,
        }
        for factor_name, weight in FACTOR_WEIGHTS.items()
    ]

    parameters = [
        {
            "name": PARAMETER_NAMES[factor_name],
            "score": round(factor_scores[factor_name], 2),
            "weight": weight,
        }
        for factor_name, weight in FACTOR_WEIGHTS.items()
    ]

    return {
        "adaptive_score": adaptive_score,
        "adaptive_threshold": _adaptive_threshold(),
        "overall_risk_score": adaptive_score,
        "overall_risk_level": _risk_level_from_score(adaptive_score),
        "weights": FACTOR_WEIGHTS,
        "factor_scores": {name: round(score, 2) for name, score in factor_scores.items()},
        "risk_drivers": risk_drivers,
        "parameters": parameters,
    }
