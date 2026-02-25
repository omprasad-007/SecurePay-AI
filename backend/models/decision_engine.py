from __future__ import annotations

from typing import Dict


def decision_from_score(score: float) -> Dict[str, str]:
    if score > 80:
        return {"risk_level": "CRITICAL", "action": "Block"}
    if score > 60:
        return {"risk_level": "HIGH", "action": "Step-Up Verification"}
    if score > 30:
        return {"risk_level": "MEDIUM", "action": "OTP"}
    return {"risk_level": "LOW", "action": "Approve"}
