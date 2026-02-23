from __future__ import annotations

import math
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


def _parse_time(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def _clamp(value: float, min_value: float = 0.0, max_value: float = 100.0) -> float:
    return max(min_value, min(max_value, value))


def _user_amount_avg(history: List[dict], user_id: str) -> float:
    amounts = [tx.get("amount", 0.0) for tx in history if tx.get("userId") == user_id]
    if not amounts:
        return 0.0
    return float(sum(amounts) / len(amounts))


def _user_score_avg(history: List[dict], user_id: str) -> float:
    scores = [tx.get("finalScore", 0.0) for tx in history if tx.get("userId") == user_id]
    scores = [s for s in scores if s]
    if not scores:
        return 50.0
    return float(sum(scores) / len(scores))


def time_weight(timestamp: str) -> float:
    hour = _parse_time(timestamp).hour
    if 0 <= hour <= 5:
        return float(os.getenv("ADAPTIVE_TIME_WEIGHT_NIGHT", "1.2"))
    if 6 <= hour <= 8:
        return float(os.getenv("ADAPTIVE_TIME_WEIGHT_EARLY", "1.1"))
    if 22 <= hour <= 23:
        return float(os.getenv("ADAPTIVE_TIME_WEIGHT_LATE", "1.15"))
    return 1.0


def merchant_weight(merchant: str | None) -> float:
    merchant = (merchant or "").lower()
    risky_keywords = ["cash", "wallet", "crypto", "loan", "unknown", "fast"]
    if any(keyword in merchant for keyword in risky_keywords):
        return float(os.getenv("ADAPTIVE_MERCHANT_WEIGHT", "1.2"))
    return 1.0


def velocity_weight(features: Dict[str, Any]) -> float:
    velocity_1h = features.get("velocity_1h", 0)
    velocity_24h = features.get("velocity_24h", 0)
    if velocity_1h >= 5:
        return 1.25
    if velocity_24h >= 15:
        return 1.15
    return 1.0


def device_familiarity_score(tx: dict, history: List[dict]) -> float:
    device_id = tx.get("deviceId")
    if not device_id:
        return 0.5
    seen = {item.get("deviceId") for item in history if item.get("userId") == tx.get("userId")}
    return 0.2 if device_id in seen else 0.8


def device_risk_score(tx: dict, history: List[dict], device_context: dict | None = None) -> float:
    familiarity = device_familiarity_score(tx, history)
    ip_risk = 0.0
    if device_context:
        ip_risk = float(device_context.get("ipRisk", 0.0))
    device_weight = 0.4 + familiarity + ip_risk
    return min(1.5, device_weight)


def dynamic_threshold(history: List[dict], user_id: str) -> float:
    base = float(os.getenv("ADAPTIVE_BASE_THRESHOLD", "70"))
    avg_score = _user_score_avg(history, user_id)
    avg_amount = _user_amount_avg(history, user_id)
    adjustment = (avg_score - 50) * 0.2
    amount_adj = min(10.0, avg_amount / 10000 * 10)
    threshold = base + adjustment + amount_adj
    return float(_clamp(threshold, 50.0, 90.0))


def adaptive_risk(
    base_results: Dict[str, Any],
    tx: dict,
    history: List[dict],
    device_context: dict | None = None,
) -> Dict[str, Any]:
    base_score = float(base_results.get("final_score", 0.0))
    features = base_results.get("features", {})

    time_mul = time_weight(tx.get("timestamp", ""))
    merchant_mul = merchant_weight(tx.get("merchant"))
    velocity_mul = velocity_weight(features)
    device_mul = device_risk_score(tx, history, device_context)

    adaptive_score = base_score * time_mul * merchant_mul * velocity_mul * device_mul
    adaptive_score = _clamp(adaptive_score)

    threshold = dynamic_threshold(history, tx.get("userId", ""))

    risk_drivers = [
        {"factor": "Base ML Score", "impact": round(base_score / 100, 2)},
        {"factor": "Time-of-Day", "impact": round(time_mul - 1.0, 2)},
        {"factor": "Merchant Risk", "impact": round(merchant_mul - 1.0, 2)},
        {"factor": "Velocity", "impact": round(velocity_mul - 1.0, 2)},
        {"factor": "Device Risk", "impact": round(device_mul - 1.0, 2)},
    ]

    return {
        "adaptive_score": adaptive_score,
        "adaptive_threshold": threshold,
        "weights": {
            "time": time_mul,
            "merchant": merchant_mul,
            "velocity": velocity_mul,
            "device": device_mul,
        },
        "risk_drivers": risk_drivers,
    }
