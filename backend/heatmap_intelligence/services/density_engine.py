from __future__ import annotations

import math
from collections import defaultdict

from ..schemas import GeographicHeatmapResponse, GeographicHeatPoint, TimePatternCell, TimePatternResponse
from ..source_models import AuditSourceTransaction
from ..utils.geo import clamp, haversine_km, heat_risk_level

W_VELOCITY = 0.2
W_AMOUNT = 0.3
W_GEO = 0.2
W_DEVICE = 0.3


def _user_stats(rows: list[AuditSourceTransaction]) -> dict[str, dict]:
    stats: dict[str, dict] = {}
    by_user: dict[str, list[AuditSourceTransaction]] = defaultdict(list)
    for row in rows:
        by_user[row.user_id].append(row)

    for user_id, items in by_user.items():
        amounts = [float(item.transaction_amount or 0.0) for item in items if float(item.transaction_amount or 0.0) > 0]
        mean = sum(amounts) / len(amounts) if amounts else 0.0

        latitudes = [float(item.geo_latitude) for item in items if item.geo_latitude is not None]
        longitudes = [float(item.geo_longitude) for item in items if item.geo_longitude is not None]
        center_lat = sum(latitudes) / len(latitudes) if latitudes else None
        center_lng = sum(longitudes) / len(longitudes) if longitudes else None

        device_counts: dict[str, int] = defaultdict(int)
        for item in items:
            if item.device_id:
                device_counts[item.device_id] += 1

        if items:
            span_seconds = max(1.0, (max(i.transaction_datetime for i in items) - min(i.transaction_datetime for i in items)).total_seconds())
            tx_per_hour = len(items) / (span_seconds / 3600)
        else:
            tx_per_hour = 0.0

        stats[user_id] = {
            "mean_amount": mean,
            "center_lat": center_lat,
            "center_lng": center_lng,
            "device_counts": device_counts,
            "tx_per_hour": tx_per_hour,
            "total": max(1, len(items)),
        }
    return stats


def _transaction_weight(row: AuditSourceTransaction, stats: dict[str, dict]) -> float:
    user = stats.get(row.user_id, {})
    mean_amount = float(user.get("mean_amount", 0.0))
    amount = float(row.transaction_amount or 0.0)
    if mean_amount > 0:
        amount_deviation = clamp(abs(amount - mean_amount) / mean_amount, 0.0, 1.0)
    else:
        amount_deviation = 0.0

    velocity_score = clamp(float(user.get("tx_per_hour", 0.0)) / 8.0, 0.0, 1.0)

    geo_anomaly = 0.0
    if row.geo_latitude is not None and row.geo_longitude is not None:
        center_lat = user.get("center_lat")
        center_lng = user.get("center_lng")
        if center_lat is not None and center_lng is not None:
            distance = haversine_km(float(row.geo_latitude), float(row.geo_longitude), float(center_lat), float(center_lng))
            geo_anomaly = clamp(distance / 1500.0, 0.0, 1.0)

    device_counts = user.get("device_counts", {})
    total = max(1, int(user.get("total", 1)))
    if row.device_id and row.device_id in device_counts:
        device_risk = 1.0 - clamp(device_counts[row.device_id] / total, 0.0, 1.0)
    else:
        device_risk = 0.5

    return 1.0 + velocity_score * W_VELOCITY + amount_deviation * W_AMOUNT + geo_anomaly * W_GEO + device_risk * W_DEVICE


def build_geographic_heatmap(rows: list[AuditSourceTransaction]) -> GeographicHeatmapResponse:
    stats = _user_stats(rows)
    grouped: dict[tuple[float, float], dict] = {}

    for row in rows:
        if row.geo_latitude is None or row.geo_longitude is None:
            continue
        key = (round(float(row.geo_latitude), 3), round(float(row.geo_longitude), 3))
        bucket = grouped.setdefault(
            key,
            {"weighted_sum": 0.0, "count": 0, "fraud_count": 0, "risk_sum": 0.0},
        )
        weight = _transaction_weight(row, stats)
        risk = float(row.risk_score or 0.0)
        bucket["weighted_sum"] += risk * weight
        bucket["risk_sum"] += risk
        bucket["count"] += 1
        if risk > 60:
            bucket["fraud_count"] += 1

    points: list[GeographicHeatPoint] = []
    for (lat, lng), bucket in grouped.items():
        total = max(1, bucket["count"])
        fraud_density = bucket["weighted_sum"] / (100.0 * total)
        heat_intensity = float(fraud_density * math.log(1 + bucket["fraud_count"] + 1))
        avg_risk = bucket["risk_sum"] / total
        points.append(
            GeographicHeatPoint(
                lat=lat,
                lng=lng,
                risk_density=round(clamp(fraud_density, 0.0, 1.0), 4),
                fraud_count=int(bucket["fraud_count"]),
                avg_risk_score=round(avg_risk, 2),
                heat_intensity=round(clamp(heat_intensity, 0.0, 3.0), 4),
                risk_level=heat_risk_level(avg_risk),
            )
        )

    points.sort(key=lambda item: (item.heat_intensity, item.avg_risk_score), reverse=True)
    return GeographicHeatmapResponse(
        points=points,
        meta={
            "total_points": len(points),
            "total_transactions": len(rows),
            "high_risk_transactions": sum(1 for row in rows if float(row.risk_score or 0.0) > 60),
        },
    )


def build_time_pattern_heatmap(rows: list[AuditSourceTransaction]) -> TimePatternResponse:
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    buckets: dict[tuple[int, int], dict] = {}

    for day in range(7):
        for hour in range(24):
            buckets[(day, hour)] = {"count": 0, "fraud_count": 0, "risk_sum": 0.0}

    for row in rows:
        day = row.transaction_datetime.weekday()
        hour = row.transaction_datetime.hour
        risk = float(row.risk_score or 0.0)

        bucket = buckets[(day, hour)]
        bucket["count"] += 1
        bucket["risk_sum"] += risk
        if risk > 60:
            bucket["fraud_count"] += 1

    matrix = []
    for day in range(7):
        for hour in range(24):
            bucket = buckets[(day, hour)]
            count = max(1, bucket["count"])
            fraud_ratio = bucket["fraud_count"] / count
            avg_risk = bucket["risk_sum"] / count
            intensity = clamp((fraud_ratio * 0.6) + ((avg_risk / 100.0) * 0.4), 0.0, 1.0)

            matrix.append(
                TimePatternCell(
                    day_index=day,
                    day_name=day_names[day],
                    hour=hour,
                    fraud_intensity=round(intensity, 4),
                    fraud_count=int(bucket["fraud_count"]),
                    avg_risk_score=round(avg_risk, 2),
                )
            )

    return TimePatternResponse(
        matrix=matrix,
        meta={
            "peak_window": max(matrix, key=lambda item: item.fraud_intensity).model_dump() if matrix else None,
            "total_transactions": len(rows),
        },
    )

