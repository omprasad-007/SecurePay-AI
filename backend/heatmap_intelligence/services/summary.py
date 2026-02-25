from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date

from ..schemas import HeatmapSummaryResponse
from ..source_models import AuditSourceTransaction
from ..utils.geo import clamp
from .clustering import DeviceAnomalyResponse, FraudClustersResponse
from .density_engine import build_time_pattern_heatmap


def _high_risk_percentage(rows: list[AuditSourceTransaction]) -> float:
    if not rows:
        return 0.0
    return (sum(1 for row in rows if float(row.risk_score or 0.0) > 60) / len(rows)) * 100.0


def _daily_timeline(rows: list[AuditSourceTransaction]) -> list[dict]:
    daily: dict[str, dict] = defaultdict(lambda: {"total": 0, "high_risk": 0, "risk_sum": 0.0})
    for row in rows:
        key = row.transaction_datetime.date().isoformat()
        item = daily[key]
        item["total"] += 1
        risk = float(row.risk_score or 0.0)
        item["risk_sum"] += risk
        if risk > 60:
            item["high_risk"] += 1

    timeline = []
    for key in sorted(daily.keys()):
        item = daily[key]
        total = max(1, item["total"])
        timeline.append(
            {
                "date": key,
                "transaction_volume": item["total"],
                "fraud_rate": round((item["high_risk"] / total) * 100.0, 2),
                "avg_risk_score": round(item["risk_sum"] / total, 2),
            }
        )
    return timeline


def _top_region(rows: list[AuditSourceTransaction]) -> str:
    counter = Counter((row.city or "Unknown") for row in rows if float(row.risk_score or 0.0) > 60)
    if not counter:
        return "No dominant region"
    region, count = counter.most_common(1)[0]
    return f"{region} ({count} high-risk txns)"


def _top_device_pattern(device_heatmap: DeviceAnomalyResponse) -> str:
    if not device_heatmap.devices:
        return "No device anomaly pattern"
    top = device_heatmap.devices[0]
    return f"{top.device_type} via {top.device_id} ({top.anomaly_score:.1f} anomaly score)"


def _top_time_window(rows: list[AuditSourceTransaction]) -> str:
    matrix = build_time_pattern_heatmap(rows).matrix
    if not matrix:
        return "No time anomaly window"
    peak = max(matrix, key=lambda item: item.fraud_intensity)
    return f"{peak.day_name} {peak.hour:02d}:00-{(peak.hour + 1) % 24:02d}:00"


def _velocity_layer(rows: list[AuditSourceTransaction]) -> list[dict]:
    buckets = Counter()
    for row in rows:
        bucket = row.transaction_datetime.replace(minute=(row.transaction_datetime.minute // 10) * 10, second=0, microsecond=0)
        buckets[(row.user_id, bucket.isoformat())] += 1
    layer = [
        {"user_id": user_id, "window": window, "count": count}
        for (user_id, window), count in buckets.items()
        if count >= 3
    ]
    layer.sort(key=lambda item: item["count"], reverse=True)
    return layer[:20]


def _amount_deviation_layer(rows: list[AuditSourceTransaction]) -> list[dict]:
    by_user_amounts: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        amount = float(row.transaction_amount or 0.0)
        if amount > 0:
            by_user_amounts[row.user_id].append(amount)

    user_mean = {user: (sum(values) / len(values)) for user, values in by_user_amounts.items() if values}
    city_scores: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        mean = user_mean.get(row.user_id)
        amount = float(row.transaction_amount or 0.0)
        if not mean or mean <= 0:
            continue
        deviation = abs(amount - mean) / mean
        city_scores[row.city or "Unknown"].append(deviation)

    layer = []
    for city, deviations in city_scores.items():
        if not deviations:
            continue
        score = sum(deviations) / len(deviations)
        layer.append({"city": city, "amount_deviation_score": round(clamp(score * 100, 0.0, 100.0), 2)})
    layer.sort(key=lambda item: item["amount_deviation_score"], reverse=True)
    return layer[:20]


def _cross_border_layer(rows: list[AuditSourceTransaction]) -> list[dict]:
    by_user_countries: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row.country:
            by_user_countries[row.user_id].add(row.country)

    flagged_users = [user_id for user_id, countries in by_user_countries.items() if len(countries) > 1]
    layer = []
    for user_id in flagged_users:
        countries = sorted(by_user_countries[user_id])
        layer.append({"user_id": user_id, "countries": countries, "cross_border_count": len(countries)})
    layer.sort(key=lambda item: item["cross_border_count"], reverse=True)
    return layer[:20]


def _fraud_ring_graph(clusters: FraudClustersResponse) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []
    seen_nodes: set[str] = set()
    for cluster in clusters.clusters:
        cluster_node = f"cluster:{cluster.cluster_id}"
        if cluster_node not in seen_nodes:
            nodes.append({"id": cluster_node, "type": "cluster", "risk_score": cluster.ring_risk_score})
            seen_nodes.add(cluster_node)

        for user in cluster.users:
            user_node = f"user:{user}"
            if user_node not in seen_nodes:
                nodes.append({"id": user_node, "type": "user"})
                seen_nodes.add(user_node)
            edges.append({"source": cluster_node, "target": user_node, "kind": "member"})

        for device in cluster.shared_devices:
            device_node = f"device:{device}"
            if device_node not in seen_nodes:
                nodes.append({"id": device_node, "type": "device"})
                seen_nodes.add(device_node)
            edges.append({"source": cluster_node, "target": device_node, "kind": "shared_device"})
    return {"nodes": nodes, "edges": edges}


def build_heatmap_summary(
    start_date: date,
    end_date: date,
    current_rows: list[AuditSourceTransaction],
    previous_rows: list[AuditSourceTransaction],
    device_heatmap: DeviceAnomalyResponse,
    clusters: FraudClustersResponse,
) -> HeatmapSummaryResponse:
    current_total = max(1, len(current_rows))
    avg_risk = sum(float(row.risk_score or 0.0) for row in current_rows) / current_total if current_rows else 0.0
    current_high_pct = _high_risk_percentage(current_rows)
    previous_high_pct = _high_risk_percentage(previous_rows)

    if previous_high_pct == 0:
        concentration_change = 100.0 if current_high_pct > 0 else 0.0
    else:
        concentration_change = ((current_high_pct - previous_high_pct) / previous_high_pct) * 100.0

    top_region = _top_region(current_rows)
    top_window = _top_time_window(current_rows)
    device_pattern = _top_device_pattern(device_heatmap)
    timeline = _daily_timeline(current_rows)

    growth_word = "increased" if concentration_change >= 0 else "decreased"
    ai_summary = (
        f"Fraud concentration {growth_word} by {abs(concentration_change):.1f}% between "
        f"{start_date.isoformat()} and {end_date.isoformat()}, centered around {top_region} "
        f"and peak time window {top_window}. Device signal indicates {device_pattern}."
    )

    layers = {
        "velocity_risk_layer": _velocity_layer(current_rows),
        "amount_deviation_layer": _amount_deviation_layer(current_rows),
        "cross_border_fraud_layer": _cross_border_layer(current_rows),
        "risk_evolution_timeline": timeline,
        "fraud_ring_visualization": _fraud_ring_graph(clusters),
    }

    return HeatmapSummaryResponse(
        overall_risk_score=round(avg_risk, 2),
        fraud_concentration_change_pct=round(concentration_change, 2),
        top_region=top_region,
        top_time_window=top_window,
        linked_device_pattern=device_pattern,
        ai_summary=ai_summary,
        timeline=timeline,
        layers=layers,
    )
