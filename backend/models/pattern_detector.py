from __future__ import annotations

from datetime import datetime, timezone
from typing import List


def _parse_time(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def detect_patterns(tx: dict, history: List[dict]) -> list[str]:
    patterns: list[str] = []
    user_id = tx.get("userId")
    now = _parse_time(tx.get("timestamp", ""))
    recent = [item for item in history if item.get("userId") == user_id]

    if recent:
        last_tx = max(recent, key=lambda item: _parse_time(item.get("timestamp", "")))
        delta = now - _parse_time(last_tx.get("timestamp", ""))
        if delta.days >= 7:
            patterns.append("Dormant Activation")

    last_hour = [
        item for item in recent if (now - _parse_time(item.get("timestamp", ""))).total_seconds() <= 3600
    ]
    micro = [item for item in last_hour if item.get("amount", 0) <= 200]
    if len(micro) >= 6:
        patterns.append("Rapid-fire microtransactions")

    smurf = [item for item in last_hour if item.get("amount", 0) <= 500]
    if len(smurf) >= 8:
        patterns.append("Smurfing")

    if any(item.get("receiverId") == user_id for item in history):
        patterns.append("Circular flow")

    return patterns
