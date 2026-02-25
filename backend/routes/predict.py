from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

from models.fraud_pipeline import score_transaction
from models.adaptive_risk import adaptive_risk
from models.decision_engine import decision_from_score
from models.pattern_detector import detect_patterns
from security import get_current_user
from utils import log_fraud_attempt, sanitize_text

router = APIRouter(prefix="", tags=["predict"])


class Location(BaseModel):
    city: str
    lat: float
    lon: float

    @field_validator("city")
    @classmethod
    def clean_city(cls, value: str) -> str:
        return sanitize_text(value)


class Transaction(BaseModel):
    id: str
    userId: str
    receiverId: str
    amount: float = Field(gt=0)
    deviceId: str
    merchant: Optional[str] = "Unknown"
    channel: Optional[str] = "UPI"
    ip: Optional[str] = "0.0.0.0"
    location: Optional[Location]
    timestamp: str
    deviceFingerprint: Optional[str] = None

    @field_validator("id", "userId", "receiverId", "deviceId", "merchant", "channel", "ip")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return sanitize_text(value)


class PredictRequest(BaseModel):
    transaction: Transaction
    history: List[Transaction] = []
    device_context: Optional[dict] = None


@router.post("/predict")
async def predict(payload: PredictRequest, user=Depends(get_current_user)):
    history = [item.model_dump() for item in payload.history]
    tx = payload.transaction.model_dump()

    results = score_transaction(tx, history)
    adaptive = adaptive_risk(results, tx, history, payload.device_context)
    decision = decision_from_score(adaptive["adaptive_score"])
    patterns = detect_patterns(tx, history)

    if decision["risk_level"] in {"HIGH", "CRITICAL"}:
        log_fraud_attempt(f"High risk transaction flagged: {tx.get('id')} user={tx.get('userId')}")

    return {
        "fraud_score": adaptive["adaptive_score"] / 100,
        "risk_level_enterprise": decision["risk_level"],
        "final_score": results["final_score"],
        "risk_level": results["risk_level"],
        "anomaly_score": results["anomaly_score"],
        "supervised_prob": results["supervised_prob"],
        "graph_risk": results["graph_risk"],
        "features": results["features"],
        "explanation": _build_explanation(results),
        "adaptive_score": adaptive["adaptive_score"],
        "adaptive_threshold": adaptive["adaptive_threshold"],
        "adaptive_risk_level": decision["risk_level"],
        "decision_action": decision["action"],
        "overall_risk_score": adaptive.get("overall_risk_score", adaptive["adaptive_score"]),
        "overall_risk_level": adaptive.get("overall_risk_level", decision["risk_level"]),
        "factor_scores": adaptive.get("factor_scores", {}),
        "parameters": adaptive.get("parameters", []),
        "risk_drivers": adaptive.get("risk_drivers", []),
        "patterns": patterns,
    }


def _build_explanation(results: dict) -> str:
    reasons = []
    features = results.get("features", {})
    if features.get("velocity_1h", 0) > 4:
        reasons.append("high transaction velocity")
    if features.get("device_change"):
        reasons.append("new device detected")
    if features.get("geo_distance_km", 0) > 200:
        reasons.append("geo-location shift")
    if features.get("blacklisted"):
        reasons.append("blacklisted receiver")
    if not reasons:
        reasons.append("normal behavioral pattern")
    return "Risk drivers: " + ", ".join(reasons)


