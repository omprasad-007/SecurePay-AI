from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List

from models.graph_model import graph_view
from models.fraud_pipeline import build_feature_dict
from security import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


class Location(BaseModel):
    city: str
    lat: float
    lon: float


class Transaction(BaseModel):
    id: str
    userId: str
    receiverId: str
    amount: float
    deviceId: str
    merchant: str | None = None
    channel: str | None = None
    ip: str | None = None
    location: Location | None = None
    timestamp: str


class HistoryRequest(BaseModel):
    history: List[Transaction] = []


@router.post("/graph")
async def graph(payload: HistoryRequest, user=Depends(get_current_user)):
    history = [item.model_dump() for item in payload.history]
    graph_data = graph_view(history)

    if history:
        features = [build_feature_dict(item, history) for item in history]
        anomaly_avg = sum(item["amount_zscore"] for item in features) / len(features)
        supervised_avg = sum(item["amount_ratio"] for item in features) / len(features) * 20
        graph_avg = 45 if len(graph_data["nodes"]) > 6 else 28
    else:
        anomaly_avg = supervised_avg = graph_avg = 0

    return {
        "graph": graph_data,
        "summary": {
            "anomaly": min(100, anomaly_avg * 10),
            "supervised": min(100, supervised_avg),
            "graph": min(100, graph_avg),
        },
    }
