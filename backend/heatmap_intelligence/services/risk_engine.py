from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from ..source_models import AuditSourceTransaction
from ..utils.geo import clamp, haversine_km


def _risk_level(score: float) -> str:
    if score <= 30:
        return "Low"
    if score <= 60:
        return "Medium"
    if score <= 80:
        return "High"
    return "Critical"


def _user_context(rows: list[AuditSourceTransaction]) -> dict[str, dict[str, Any]]:
    by_user: dict[str, list[AuditSourceTransaction]] = defaultdict(list)
    for row in rows:
        by_user[row.user_id].append(row)

    context: dict[str, dict[str, Any]] = {}
    for user_id, items in by_user.items():
        ordered = sorted(items, key=lambda item: item.transaction_datetime)
        amounts = [float(item.transaction_amount or 0.0) for item in ordered if float(item.transaction_amount or 0.0) > 0]
        average_amount = (sum(amounts) / len(amounts)) if amounts else 0.0
        device_counter = Counter(item.device_id or "unknown-device" for item in ordered)
        ip_counter = Counter(item.ip_address or "unknown-ip" for item in ordered)
        high_risk_count = sum(1 for item in ordered if float(item.risk_score or 0.0) > 60)
        context[user_id] = {
            "ordered": ordered,
            "average_amount": average_amount,
            "device_counter": device_counter,
            "ip_counter": ip_counter,
            "high_risk_count": high_risk_count,
            "transaction_count": len(ordered),
        }
    return context


def _shared_device_users(rows: list[AuditSourceTransaction]) -> dict[str, set[str]]:
    by_device: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        device = row.device_id or "unknown-device"
        by_device[device].add(row.user_id)
    return by_device


def _user_degree_centrality(rows: list[AuditSourceTransaction]) -> dict[str, float]:
    graph: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        user = f"user:{row.user_id}"
        graph[user].add(f"device:{row.device_id or 'unknown-device'}")
        graph[user].add(f"ip:{row.ip_address or 'unknown-ip'}")
        graph[user].add(f"merchant:{row.merchant_name or 'unknown-merchant'}")
    node_count = max(1, len(graph))
    return {
        key.split(":", 1)[1]: clamp(len(neighbors) / max(1, node_count - 1), 0.0, 1.0)
        for key, neighbors in graph.items()
        if key.startswith("user:")
    }


def compute_transaction_risk_scores(
    *,
    rows: list[AuditSourceTransaction],
    cluster_by_user: dict[str, str],
    regulatory_amount_threshold: float,
) -> dict[str, dict[str, Any]]:
    user_ctx = _user_context(rows)
    shared_device_map = _shared_device_users(rows)
    centrality = _user_degree_centrality(rows)

    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        user_id = row.user_id
        context = user_ctx.get(user_id, {})
        ordered = context.get("ordered", [])

        amount = float(row.transaction_amount or 0.0)
        average_amount = float(context.get("average_amount", 0.0))
        amount_deviation = clamp(abs(amount - average_amount) / average_amount, 0.0, 1.0) if average_amount > 0 else 0.1

        recent_window_count = sum(
            1
            for item in ordered
            if abs((row.transaction_datetime - item.transaction_datetime).total_seconds()) <= 3600
        )
        frequency_spike = clamp((recent_window_count - 1) / 6.0, 0.0, 1.0)
        hour = row.transaction_datetime.hour
        time_abnormality = 0.8 if 1 <= hour <= 4 else (0.5 if hour >= 23 or hour <= 5 else 0.2)
        transaction_risk = clamp((amount_deviation * 0.45) + (frequency_spike * 0.35) + (time_abnormality * 0.20), 0.0, 1.0)

        device_counter: Counter = context.get("device_counter", Counter())
        device = row.device_id or "unknown-device"
        device_change_frequency = 1.0 - clamp(device_counter.get(device, 0) / max(1, context.get("transaction_count", 1)), 0.0, 1.0)

        geo_distance = 0.0
        previous_items = [item for item in ordered if item.transaction_datetime < row.transaction_datetime]
        if previous_items and row.geo_latitude is not None and row.geo_longitude is not None:
            last = previous_items[-1]
            if last.geo_latitude is not None and last.geo_longitude is not None:
                geo_distance = haversine_km(
                    float(last.geo_latitude),
                    float(last.geo_longitude),
                    float(row.geo_latitude),
                    float(row.geo_longitude),
                )
        geo_distance_risk = clamp(geo_distance / 1500.0, 0.0, 1.0)

        ip_counter: Counter = context.get("ip_counter", Counter())
        ip = row.ip_address or "unknown-ip"
        new_ip_probability = 1.0 - clamp(ip_counter.get(ip, 0) / max(1, context.get("transaction_count", 1)), 0.0, 1.0)
        behavioral_risk = clamp(
            (device_change_frequency * 0.35) + (geo_distance_risk * 0.35) + (new_ip_probability * 0.30),
            0.0,
            1.0,
        )

        connected_to_cluster = 1.0 if cluster_by_user.get(user_id) else 0.0
        shared_device_risk = clamp((len(shared_device_map.get(device, set())) - 1) / 5.0, 0.0, 1.0)
        centrality_score = float(centrality.get(user_id, 0.0))
        network_risk = clamp(
            (connected_to_cluster * 0.45) + (shared_device_risk * 0.30) + (centrality_score * 0.25),
            0.0,
            1.0,
        )

        historical_fraud_probability = clamp(
            float(context.get("high_risk_count", 0)) / max(1, context.get("transaction_count", 1)),
            0.0,
            1.0,
        )

        anomaly_score = clamp(
            (0.35 * transaction_risk)
            + (0.30 * behavioral_risk)
            + (0.20 * network_risk)
            + (0.15 * historical_fraud_probability),
            0.0,
            1.0,
        )

        ml_probability = clamp(float(row.risk_score or 0.0) / 100.0, 0.0, 1.0)
        rule_based_score = anomaly_score
        final_risk = clamp((0.6 * ml_probability) + (0.4 * rule_based_score), 0.0, 1.0) * 100.0

        compliance_review = (
            final_risk > 80
            or bool(cluster_by_user.get(user_id))
            or amount >= regulatory_amount_threshold
        )

        output[row.transaction_id] = {
            "transaction_features": {
                "amount_deviation": round(amount_deviation * 100, 2),
                "frequency_spike": round(frequency_spike * 100, 2),
                "time_of_day_abnormality": round(time_abnormality * 100, 2),
            },
            "behavioral_features": {
                "device_change_frequency": round(device_change_frequency * 100, 2),
                "geo_distance_from_last_login_km": round(geo_distance, 2),
                "new_ip_probability": round(new_ip_probability * 100, 2),
            },
            "network_features": {
                "connected_to_known_fraud_cluster": bool(cluster_by_user.get(user_id)),
                "shared_device_risk": round(shared_device_risk * 100, 2),
                "fraud_graph_centrality": round(centrality_score * 100, 2),
            },
            "component_scores": {
                "transaction_risk": round(transaction_risk * 100, 2),
                "behavioral_risk": round(behavioral_risk * 100, 2),
                "network_risk": round(network_risk * 100, 2),
                "historical_fraud_probability": round(historical_fraud_probability * 100, 2),
            },
            "anomaly_score": round(anomaly_score * 100, 2),
            "ml_probability": round(ml_probability, 4),
            "rule_based_score": round(rule_based_score * 100, 2),
            "final_risk": round(final_risk, 2),
            "final_risk_level": _risk_level(final_risk),
            "compliance_review": compliance_review,
            "cluster_id": cluster_by_user.get(user_id),
        }
    return output
