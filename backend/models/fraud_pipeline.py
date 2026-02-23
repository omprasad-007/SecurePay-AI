from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Tuple

import numpy as np

from .anomaly import IsolationForestAnomaly
from .supervised import SupervisedClassifier
from .graph_model import graph_risk_score

FEATURE_ORDER = [
    "amount",
    "hour",
    "day_of_week",
    "velocity_1h",
    "velocity_24h",
    "device_change",
    "geo_distance_km",
    "new_beneficiary",
    "merchant_risk",
    "blacklisted",
    "ip_change",
    "amount_ratio",
    "amount_zscore",
]

BLACKLISTED_RECEIVERS = {"MERCH99", "RISKY001"}
SUSPICIOUS_MERCHANTS = {"UnknownWallet", "CashChain", "FastLoan"}


def _parse_time(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
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


def _user_history(history: list[dict], user_id: str) -> list[dict]:
    return [tx for tx in history if tx.get("userId") == user_id]


def _last_transaction(history: list[dict], user_id: str) -> dict | None:
    user_tx = _user_history(history, user_id)
    if not user_tx:
        return None
    return max(user_tx, key=lambda tx: _parse_time(tx.get("timestamp", "")))


def _velocity(history: list[dict], user_id: str, window_hours: int) -> int:
    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - window_hours * 3600
    return sum(
        1
        for tx in history
        if tx.get("userId") == user_id and _parse_time(tx.get("timestamp", "")).timestamp() >= cutoff
    )


def _amount_stats(history: list[dict], user_id: str) -> Tuple[float, float]:
    amounts = [tx.get("amount", 0) for tx in history if tx.get("userId") == user_id]
    if not amounts:
        return 0.0, 1.0
    mean = float(np.mean(amounts))
    std = float(np.std(amounts) + 1e-3)
    return mean, std


def build_feature_dict(tx: dict, history: list[dict]) -> dict:
    timestamp = _parse_time(tx.get("timestamp", ""))
    last_tx = _last_transaction(history, tx["userId"])
    amount_mean, amount_std = _amount_stats(history, tx["userId"])

    geo_distance = 0.0
    if last_tx and last_tx.get("location") and tx.get("location"):
        geo_distance = _haversine(
            last_tx["location"]["lat"],
            last_tx["location"]["lon"],
            tx["location"]["lat"],
            tx["location"]["lon"],
        )

    device_change = 1 if last_tx and last_tx.get("deviceId") != tx.get("deviceId") else 0
    ip_change = 1 if last_tx and last_tx.get("ip") != tx.get("ip") else 0

    velocity_1h = _velocity(history, tx["userId"], 1)
    velocity_24h = _velocity(history, tx["userId"], 24)

    new_beneficiary = 0
    if history:
        receivers = {item.get("receiverId") for item in history if item.get("userId") == tx["userId"]}
        new_beneficiary = 0 if tx.get("receiverId") in receivers else 1

    merchant_risk = 1 if tx.get("merchant") in SUSPICIOUS_MERCHANTS else 0
    blacklisted = 1 if tx.get("receiverId") in BLACKLISTED_RECEIVERS else 0

    amount_ratio = (tx.get("amount", 0) / amount_mean) if amount_mean > 0 else 1.0
    amount_zscore = abs(tx.get("amount", 0) - amount_mean) / amount_std

    return {
        "amount": float(tx.get("amount", 0)),
        "hour": timestamp.hour,
        "day_of_week": timestamp.weekday(),
        "velocity_1h": velocity_1h,
        "velocity_24h": velocity_24h,
        "device_change": device_change,
        "geo_distance_km": geo_distance,
        "new_beneficiary": new_beneficiary,
        "merchant_risk": merchant_risk,
        "blacklisted": blacklisted,
        "ip_change": ip_change,
        "amount_ratio": amount_ratio,
        "amount_zscore": amount_zscore,
    }


def feature_vector(feature_dict: dict) -> np.ndarray:
    return np.array([feature_dict.get(name, 0.0) for name in FEATURE_ORDER], dtype=float)


def score_transaction(tx: dict, history: list[dict]) -> dict:
    history = history or []
    history_features = [build_feature_dict(item, history) for item in history]
    history_vectors = np.array([feature_vector(item) for item in history_features]) if history_features else np.array([])

    target_features = build_feature_dict(tx, history)
    target_vector = feature_vector(target_features)

    anomaly_model = IsolationForestAnomaly()
    supervised_model = SupervisedClassifier()

    anomaly_score = anomaly_model.score(target_vector, history_vectors)
    supervised_prob = supervised_model.predict(target_vector, history_vectors, history_features)
    graph_risk = graph_risk_score(tx, history)

    final_score = 0.4 * anomaly_score + 0.4 * supervised_prob + 0.2 * graph_risk
    if final_score > 70:
        risk_level = "High"
    elif final_score >= 40:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return {
        "anomaly_score": anomaly_score,
        "supervised_prob": supervised_prob,
        "graph_risk": graph_risk,
        "final_score": float(final_score),
        "risk_level": risk_level,
        "features": target_features,
    }
