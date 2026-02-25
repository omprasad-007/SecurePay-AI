from __future__ import annotations

import base64
import json
import math
from collections import Counter, deque
from datetime import datetime, timezone
from typing import Any

from .graph_model import graph_risk_score

FORMULA_WEIGHTS: dict[str, float] = {
    "Amount Deviation": 0.30,
    "Location Anomaly": 0.20,
    "Velocity Risk": 0.15,
    "Merchant Novelty": 0.15,
    "Graph Risk": 0.10,
    "Account Risk": 0.10,
}

PARAMETER_DISPLAY_ORDER = [
    "Amount Deviation",
    "Velocity Risk",
    "Merchant Novelty",
    "Location Anomaly",
    "Time Anomaly",
    "Graph Risk",
    "Account Risk",
]

PARAMETER_WEIGHTS: dict[str, float] = {
    "Amount Deviation": 0.30,
    "Velocity Risk": 0.15,
    "Merchant Novelty": 0.15,
    "Location Anomaly": 0.20,
    "Time Anomaly": 0.0,
    "Graph Risk": 0.10,
    "Account Risk": 0.10,
}


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, min_value: float = 0.0, max_value: float = 100.0) -> float:
    return max(min_value, min(max_value, value))


def _parse_ts(value: Any) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
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


def _safe_location(raw_location: Any) -> dict[str, Any]:
    if not isinstance(raw_location, dict):
        return {}
    return {
        "city": str(raw_location.get("city") or "Unknown").strip(),
        "lat": _to_float(raw_location.get("lat"), 0.0),
        "lon": _to_float(raw_location.get("lon"), 0.0),
    }


def _decode_history(history_payload: str | None) -> list[dict]:
    if not history_payload:
        return []
    if len(history_payload) > 200_000:
        raise ValueError("History payload is too large")
    try:
        padded = history_payload + ("=" * ((4 - len(history_payload) % 4) % 4))
        decoded = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
        data = json.loads(decoded)
    except Exception as exc:
        raise ValueError("Invalid history payload") from exc

    if not isinstance(data, list):
        return []

    normalized: list[dict] = []
    for index, item in enumerate(data[:300]):
        if not isinstance(item, dict):
            continue

        normalized.append(
            {
                "id": str(item.get("id") or f"TXN{index + 1}"),
                "userId": str(item.get("userId") or item.get("user_id") or item.get("uid") or ""),
                "receiverId": str(item.get("receiverId") or ""),
                "merchant": str(item.get("merchant") or "Unknown"),
                "amount": _to_float(item.get("amount"), 0.0),
                "deviceId": str(item.get("deviceId") or ""),
                "ip": str(item.get("ip") or ""),
                "timestamp": str(item.get("timestamp") or ""),
                "location": _safe_location(item.get("location")),
                "finalScore": _to_float(item.get("finalScore") or item.get("final_score"), 0.0),
                "riskLevel": str(item.get("riskLevel") or item.get("risk_level") or ""),
                "features": item.get("features") if isinstance(item.get("features"), dict) else {},
            }
        )

    return normalized


def _risk_level(score: float) -> str:
    if score <= 30:
        return "Low"
    if score <= 60:
        return "Medium"
    if score <= 80:
        return "High"
    return "Critical"


def _amount_risk(amount: float, avg_amount: float, std_amount: float) -> float:
    if avg_amount <= 0:
        return 10.0

    ratio = amount / avg_amount
    if ratio >= 5:
        score = 95.0
    elif ratio >= 3:
        score = 80.0
    elif ratio >= 2:
        score = 60.0
    elif ratio >= 1.5:
        score = 30.0
    else:
        score = 10.0

    if std_amount > 0:
        z_score = abs(amount - avg_amount) / std_amount
        if z_score >= 3:
            score = max(score, 80.0)
        elif z_score >= 2:
            score = max(score, 60.0)

    return _clamp(score)


def _velocity_risk(window_count: int) -> float:
    if window_count >= 6:
        return 90.0
    if window_count >= 4:
        return 70.0
    if window_count >= 2:
        return 40.0
    return 5.0


def _merchant_risk(prior_merchant_count: int, merchant_was_flagged: bool) -> float:
    if merchant_was_flagged:
        return 90.0
    if prior_merchant_count >= 2:
        return 5.0
    if prior_merchant_count == 1:
        return 40.0
    return 70.0


def _location_risk(
    city: str,
    city_seen_count: int,
    total_seen_count: int,
    prev_location: dict[str, Any] | None,
    curr_location: dict[str, Any] | None,
    prev_ts: datetime | None,
    curr_ts: datetime,
) -> float:
    normalized_city = city.strip().lower() if city else ""

    if total_seen_count <= 0:
        base = 40.0
    elif normalized_city and city_seen_count <= 0:
        base = 70.0
    else:
        freq = city_seen_count / max(1, total_seen_count)
        base = 10.0 if freq >= 0.20 else 40.0

    if prev_location and curr_location:
        distance = _haversine(
            _to_float(prev_location.get("lat"), 0.0),
            _to_float(prev_location.get("lon"), 0.0),
            _to_float(curr_location.get("lat"), 0.0),
            _to_float(curr_location.get("lon"), 0.0),
        )
        if distance > 1000 and prev_ts is not None:
            hours = abs((curr_ts - prev_ts).total_seconds()) / 3600
            if hours <= 6:
                base += 15

    return _clamp(base)


def _time_anomaly_risk(hour: int, common_hours: set[int]) -> float:
    if 1 <= hour <= 4:
        return 80.0
    if hour in common_hours:
        return 5.0
    return 30.0


def _account_risk(
    is_new_device: bool,
    is_ip_change: bool,
    failed_login_attempts: int,
) -> float:
    anomaly_count = int(is_new_device) + int(is_ip_change) + int(failed_login_attempts >= 3)
    if anomaly_count >= 2:
        return 90.0
    if failed_login_attempts >= 3:
        return 70.0
    if is_new_device:
        return 50.0
    return 5.0


def _score_transaction_factors(transactions: list[dict]) -> tuple[list[dict], dict[str, float]]:
    if not transactions:
        return [], {name: 0.0 for name in PARAMETER_DISPLAY_ORDER}

    sorted_tx = sorted(transactions, key=lambda tx: _parse_ts(tx.get("timestamp")))
    amounts = [max(0.0, _to_float(tx.get("amount"), 0.0)) for tx in sorted_tx]

    avg_amount = sum(amounts) / len(amounts) if amounts else 0.0
    variance = sum((amount - avg_amount) ** 2 for amount in amounts) / len(amounts) if amounts else 0.0
    std_amount = math.sqrt(variance)

    hour_counter = Counter(_parse_ts(tx.get("timestamp")).hour for tx in sorted_tx)
    common_hours = {hour for hour, _ in hour_counter.most_common(8)}

    rolling_window: deque[datetime] = deque()
    merchant_seen = Counter()
    city_seen = Counter()
    seen_devices: set[str] = set()
    flagged_merchants: set[str] = set()

    prior_history: list[dict] = []
    scored: list[dict] = []

    aggregate = {name: 0.0 for name in PARAMETER_DISPLAY_ORDER}

    prev_tx: dict | None = None

    for tx in sorted_tx:
        tx_time = _parse_ts(tx.get("timestamp"))
        while rolling_window and (tx_time - rolling_window[0]).total_seconds() > 600:
            rolling_window.popleft()
        rolling_window.append(tx_time)

        location = tx.get("location") if isinstance(tx.get("location"), dict) else {}
        city = str(location.get("city") or "Unknown")
        city_key = city.strip().lower()

        merchant = str(tx.get("merchant") or "Unknown")
        merchant_key = merchant.strip().lower()

        amount_score = _amount_risk(_to_float(tx.get("amount"), 0.0), avg_amount, std_amount)
        velocity_score = _velocity_risk(len(rolling_window))
        merchant_score = _merchant_risk(merchant_seen[merchant_key], merchant_key in flagged_merchants)

        prev_location = prev_tx.get("location") if prev_tx else None
        prev_ts = _parse_ts(prev_tx.get("timestamp")) if prev_tx else None
        location_score = _location_risk(
            city,
            city_seen[city_key],
            sum(city_seen.values()),
            prev_location if isinstance(prev_location, dict) else None,
            location,
            prev_ts,
            tx_time,
        )

        hour = tx_time.hour
        time_score = _time_anomaly_risk(hour, common_hours)

        failed_attempts = int(_to_float(tx.get("features", {}).get("failed_login_attempts"), 0.0))
        is_new_device = bool(tx.get("deviceId")) and tx.get("deviceId") not in seen_devices and len(seen_devices) > 0
        is_ip_change = bool(prev_tx and tx.get("ip") and prev_tx.get("ip") and tx.get("ip") != prev_tx.get("ip"))
        account_score = _account_risk(is_new_device, is_ip_change, failed_attempts)

        graph_score = _clamp(graph_risk_score(tx, prior_history))

        factors = {
            "Amount Deviation": amount_score,
            "Velocity Risk": velocity_score,
            "Merchant Novelty": merchant_score,
            "Location Anomaly": location_score,
            "Time Anomaly": time_score,
            "Graph Risk": graph_score,
            "Account Risk": account_score,
        }

        weighted_score = sum(factors[name] * FORMULA_WEIGHTS[name] for name in FORMULA_WEIGHTS)
        weighted_score = _clamp(weighted_score)
        base_model_score = _clamp(_to_float(tx.get("finalScore"), 0.0))
        effective_risk_score = max(weighted_score, base_model_score)

        tx_confidence = int(
            round(
                _clamp(
                    45
                    + min(25, len(prior_history)) * 1.4
                    + (20 if tx.get("location") else 0)
                    + (15 if tx.get("merchant") else 0)
                    + (10 if tx.get("deviceId") else 0),
                    35,
                    98,
                )
            )
        )

        weighted_parts = {
            name: factors[name] * PARAMETER_WEIGHTS[name]
            for name in PARAMETER_DISPLAY_ORDER
        }
        top_factors = [
            {
                "name": name,
                "score": round(factors[name], 2),
                "contribution": round(weighted_parts[name], 2),
            }
            for name in sorted(weighted_parts, key=lambda key: weighted_parts[key], reverse=True)
            if PARAMETER_WEIGHTS[name] > 0
        ][:3]

        scored_tx = {
            **tx,
            "risk_score": round(effective_risk_score, 2),
            "risk_level": _risk_level(effective_risk_score),
            "model_confidence": tx_confidence,
            "factor_scores": factors,
            "top_factors": top_factors,
        }
        scored.append(scored_tx)

        for name in PARAMETER_DISPLAY_ORDER:
            aggregate[name] += factors[name]

        if effective_risk_score > 60:
            flagged_merchants.add(merchant_key)

        merchant_seen[merchant_key] += 1
        city_seen[city_key] += 1
        if tx.get("deviceId"):
            seen_devices.add(tx.get("deviceId"))

        prior_history.append(tx)
        prev_tx = tx

    total = len(scored)
    aggregate = {name: round((value / total), 2) for name, value in aggregate.items()}

    return scored, aggregate


def _parameter_explanation(name: str, score: float, weighted_contribution: float) -> str:
    if name == "Amount Deviation":
        return f"Amount behavior indicates {score:.1f}/100 risk against baseline spending. Weighted impact is {weighted_contribution:.1f} points."
    if name == "Velocity Risk":
        return f"Transaction burst intensity contributes {score:.1f}/100 risk with {weighted_contribution:.1f} weighted points."
    if name == "Merchant Novelty":
        return f"Merchant familiarity profile contributes {score:.1f}/100 risk and {weighted_contribution:.1f} weighted points."
    if name == "Location Anomaly":
        return f"Geo pattern variance is {score:.1f}/100, adding {weighted_contribution:.1f} weighted points."
    if name == "Time Anomaly":
        return f"Time-window anomaly is {score:.1f}/100. This parameter is informational in the current overall formula."
    if name == "Graph Risk":
        return f"Counterparty graph connectivity contributes {score:.1f}/100 risk and {weighted_contribution:.1f} weighted points."
    return f"Account behavior contributes {score:.1f}/100 risk and {weighted_contribution:.1f} weighted points."


def _overall_confidence(scored_txs: list[dict]) -> int:
    if not scored_txs:
        return 0
    tx_count = len(scored_txs)
    base = 50 + min(30, tx_count) * 1.1
    quality = 0.0
    for tx in scored_txs:
        quality += 1 if tx.get("merchant") else 0
        quality += 1 if tx.get("location") else 0
        quality += 1 if tx.get("deviceId") else 0
        quality += 1 if tx.get("timestamp") else 0
    quality_ratio = quality / max(1, tx_count * 4)
    score = base + quality_ratio * 20
    return int(round(_clamp(score, 35, 98)))


def _build_overall_explanations(
    scored_txs: list[dict],
    parameter_scores: dict[str, float],
) -> tuple[str, str]:
    if not scored_txs:
        return (
            "No transactions available to evaluate account risk.",
            "Add transactions to establish baseline behavior and generate explainable risk signals.",
        )

    amounts = [_to_float(tx.get("amount"), 0.0) for tx in scored_txs if _to_float(tx.get("amount"), 0.0) > 0]
    avg_amount = sum(amounts) / len(amounts) if amounts else 0.0
    latest_amount = _to_float(scored_txs[-1].get("amount"), 0.0)
    deviation_pct = (abs(latest_amount - avg_amount) / avg_amount * 100) if avg_amount > 0 else 0.0

    amount_risk = parameter_scores.get("Amount Deviation", 0.0)
    merchant_risk = parameter_scores.get("Merchant Novelty", 0.0)
    velocity_risk = parameter_scores.get("Velocity Risk", 0.0)
    location_risk = parameter_scores.get("Location Anomaly", 0.0)

    if amount_risk >= 60 and merchant_risk >= 55:
        summary = "Risk elevated due to unusual spending and new merchant activity."
    elif velocity_risk >= 60:
        summary = "Risk elevated due to rapid transaction velocity against normal behavior."
    elif location_risk >= 60:
        summary = "Risk elevated due to abnormal geolocation movement patterns."
    else:
        summary = "Risk profile remains controlled with monitored behavioral deviations."

    detailed = (
        f"Current behavior is benchmarked against the user baseline. Latest spend is INR {latest_amount:.2f} "
        f"versus historical average INR {avg_amount:.2f}, indicating {deviation_pct:.1f}% spending deviation. "
        f"Location anomaly is {location_risk:.1f}/100 and velocity risk is {velocity_risk:.1f}/100 based on recent activity cadence."
    )

    return summary, detailed


def build_risk_overview(history_payload: str | None, current_user: dict[str, Any]) -> dict[str, Any]:
    history = _decode_history(history_payload)

    user_uid = str((current_user or {}).get("uid") or (current_user or {}).get("user_id") or "")
    if user_uid and user_uid != "dev":
        history = [
            tx
            for tx in history
            if str(tx.get("userId") or tx.get("user_id") or tx.get("uid") or "") == user_uid
        ]

    if not history:
        return {
            "overall_risk_score": 0,
            "message": "No transactions available to calculate risk.",
        }

    scored_txs, parameter_scores = _score_transaction_factors(history)

    overall_score = _clamp(
        sum(parameter_scores[name] * FORMULA_WEIGHTS[name] for name in FORMULA_WEIGHTS)
    )
    overall_level = _risk_level(overall_score)
    confidence = _overall_confidence(scored_txs)

    summary_explanation, detailed_explanation = _build_overall_explanations(scored_txs, parameter_scores)

    weighted_values = {
        name: round(parameter_scores[name] * PARAMETER_WEIGHTS[name], 2)
        for name in PARAMETER_DISPLAY_ORDER
    }

    parameters = []
    for name in PARAMETER_DISPLAY_ORDER:
        weighted = weighted_values[name]
        contribution_pct = (weighted / overall_score * 100) if overall_score > 0 else 0.0
        parameters.append(
            {
                "name": name,
                "score": round(parameter_scores[name], 2),
                "weight": round(PARAMETER_WEIGHTS[name] * 100, 2),
                "contribution": round(_clamp(contribution_pct), 2),
                "detailed_explanation": _parameter_explanation(name, parameter_scores[name], weighted),
            }
        )

    high_risk_transactions = []
    for tx in scored_txs:
        risk_score = _to_float(tx.get("risk_score"), 0.0)
        if risk_score <= 60:
            continue

        breakdown = []
        for name in PARAMETER_DISPLAY_ORDER:
            weight = PARAMETER_WEIGHTS[name]
            weighted_value = tx["factor_scores"][name] * weight
            contribution_pct = (weighted_value / risk_score * 100) if risk_score > 0 else 0
            breakdown.append(
                {
                    "name": name,
                    "score": round(tx["factor_scores"][name], 2),
                    "weight": round(weight * 100, 2),
                    "contribution": round(_clamp(contribution_pct), 2),
                }
            )

        high_risk_transactions.append(
            {
                "transaction_id": tx.get("id"),
                "merchant": tx.get("merchant") or "Unknown",
                "amount": round(_to_float(tx.get("amount"), 0.0), 2),
                "location": (tx.get("location") or {}).get("city") or "Unknown",
                "risk_score": round(risk_score, 2),
                "risk_level": tx.get("risk_level"),
                "why_flagged": {
                    "top_factors": tx.get("top_factors", []),
                    "parameter_breakdown": breakdown,
                    "model_confidence": tx.get("model_confidence", confidence),
                },
            }
        )

    return {
        "overall_risk_score": round(overall_score, 2),
        "overall_risk_level": overall_level,
        "confidence": confidence,
        "last_calculated_at": datetime.now(timezone.utc).isoformat(),
        "summary_explanation": summary_explanation,
        "detailed_explanation": detailed_explanation,
        "parameters": parameters,
        "high_risk_transactions": high_risk_transactions,
    }
