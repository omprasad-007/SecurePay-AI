from __future__ import annotations

from collections import Counter, defaultdict

from ..schemas import ZoneDrilldownResponse
from ..source_models import AuditSourceTransaction
from ..utils.geo import device_type_from_id, heat_risk_level


def build_zone_drilldown(rows: list[AuditSourceTransaction], lat: float, lng: float) -> ZoneDrilldownResponse:
    total = len(rows)
    if total == 0:
        return ZoneDrilldownResponse(
            total_transactions=0,
            fraud_percentage=0.0,
            top_users=[],
            top_devices=[],
            risk_breakdown={"Low": 0, "Medium": 0, "High": 0, "Critical": 0},
            ai_summary=f"No transactions found near ({lat:.4f}, {lng:.4f}) for selected period.",
        )

    high = [row for row in rows if float(row.risk_score or 0.0) > 60]
    fraud_percentage = (len(high) / total) * 100

    user_counter = Counter(row.user_id for row in rows)
    top_users = [{"user_id": user_id, "transaction_count": count} for user_id, count in user_counter.most_common(5)]

    device_counter: Counter[tuple[str, str]] = Counter()
    for row in rows:
        did = row.device_id or "unknown-device"
        device_counter[(did, device_type_from_id(did))] += 1
    top_devices = [
        {"device_id": device_id, "device_type": device_type, "transaction_count": count}
        for (device_id, device_type), count in device_counter.most_common(5)
    ]

    risk_breakdown = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    reasons = Counter()
    for row in rows:
        level = heat_risk_level(float(row.risk_score or 0.0))
        risk_breakdown[level] = risk_breakdown.get(level, 0) + 1
        for reason in row.risk_reasons or []:
            reasons[reason] += 1

    peak_reasons = ", ".join(reason for reason, _ in reasons.most_common(3)) or "no dominant patterns"
    top_user = top_users[0]["user_id"] if top_users else "none"
    ai_summary = (
        f"Zone centered near ({lat:.4f}, {lng:.4f}) has {fraud_percentage:.1f}% high-risk transactions. "
        f"Top activity is linked to user {top_user} with dominant risk drivers: {peak_reasons}."
    )

    return ZoneDrilldownResponse(
        total_transactions=total,
        fraud_percentage=round(fraud_percentage, 2),
        top_users=top_users,
        top_devices=top_devices,
        risk_breakdown=risk_breakdown,
        ai_summary=ai_summary,
    )

