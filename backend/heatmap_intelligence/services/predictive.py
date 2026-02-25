from __future__ import annotations

from collections import defaultdict

from ..config import settings
from ..schemas import PredictiveRiskResponse, PredictiveRiskZoneRecord
from ..source_models import AuditSourceTransaction
from ..utils.geo import clamp


def build_predictive_zones(rows: list[AuditSourceTransaction]) -> PredictiveRiskResponse:
    if not rows:
        return PredictiveRiskResponse(zones=[], meta={"zone_count": 0, "escalation_count": 0})

    ordered = sorted(rows, key=lambda item: item.transaction_datetime)
    midpoint = len(ordered) // 2
    first_half = ordered[:midpoint] if midpoint > 0 else ordered
    second_half = ordered[midpoint:] if midpoint > 0 else ordered

    def group(items: list[AuditSourceTransaction]) -> dict[tuple[str | None, str | None, str | None], dict]:
        grouped: dict[tuple[str | None, str | None, str | None], dict] = defaultdict(
            lambda: {
                "total": 0,
                "high_risk": 0,
                "risk_sum": 0.0,
                "lat_sum": 0.0,
                "lng_sum": 0.0,
                "geo_count": 0,
            }
        )
        for row in items:
            key = (row.city, row.state, row.country)
            bucket = grouped[key]
            bucket["total"] += 1
            risk = float(row.risk_score or 0.0)
            bucket["risk_sum"] += risk
            if risk > 60:
                bucket["high_risk"] += 1
            if row.geo_latitude is not None and row.geo_longitude is not None:
                bucket["lat_sum"] += float(row.geo_latitude)
                bucket["lng_sum"] += float(row.geo_longitude)
                bucket["geo_count"] += 1
        return grouped

    prev = group(first_half)
    curr = group(second_half)

    zones: list[PredictiveRiskZoneRecord] = []
    keys = set(prev.keys()) | set(curr.keys())
    for key in keys:
        current = curr.get(key, {"total": 0, "high_risk": 0, "risk_sum": 0.0, "geo_count": 0, "lat_sum": 0.0, "lng_sum": 0.0})
        previous = prev.get(key, {"total": 0, "high_risk": 0, "risk_sum": 0.0, "geo_count": 0, "lat_sum": 0.0, "lng_sum": 0.0})

        current_total = max(1, current["total"])
        previous_total = max(1, previous["total"])
        current_density = current["high_risk"] / current_total
        previous_density = previous["high_risk"] / previous_total

        growth_rate = (current_density - previous_density) / max(0.05, previous_density if previous_density > 0 else 0.05)
        tx_velocity = (current["total"] - previous["total"]) / previous_total
        avg_risk = (current["risk_sum"] / current_total) if current_total else 0.0

        predicted = (
            (avg_risk / 100.0) * 0.5
            + clamp(growth_rate, -1.0, 2.0) * 0.3
            + clamp(tx_velocity, -1.0, 3.0) * 0.2
        ) * 100
        predicted = round(clamp(predicted, 0.0, 100.0), 2)

        escalating = growth_rate > settings.predictive_growth_threshold or predicted > 70
        label = "Predicted Risk Escalation" if escalating else "Monitor"

        geo_count = current["geo_count"] or previous["geo_count"]
        if geo_count:
            lat = (current["lat_sum"] + previous["lat_sum"]) / max(1, current["geo_count"] + previous["geo_count"])
            lng = (current["lng_sum"] + previous["lng_sum"]) / max(1, current["geo_count"] + previous["geo_count"])
        else:
            lat = None
            lng = None

        zones.append(
            PredictiveRiskZoneRecord(
                city=key[0],
                state=key[1],
                country=key[2],
                geo_latitude=round(lat, 6) if lat is not None else None,
                geo_longitude=round(lng, 6) if lng is not None else None,
                historical_density=round(previous_density, 4),
                growth_rate=round(growth_rate, 4),
                transaction_growth_velocity=round(tx_velocity, 4),
                predicted_risk_score=predicted,
                label=label,
            )
        )

    zones.sort(key=lambda item: item.predicted_risk_score, reverse=True)
    return PredictiveRiskResponse(
        zones=zones,
        meta={
            "zone_count": len(zones),
            "escalation_count": sum(1 for zone in zones if zone.label == "Predicted Risk Escalation"),
        },
    )

