from __future__ import annotations

import importlib
import pickle
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier


def _build_labels(feature_dicts: list[dict]) -> np.ndarray:
    labels = []
    for features in feature_dicts:
        risk = 0
        if features.get("amount", 0) > 8000:
            risk += 1
        if features.get("velocity_1h", 0) > 4:
            risk += 1
        if features.get("geo_distance_km", 0) > 200:
            risk += 1
        if features.get("device_change", 0) > 0 and features.get("amount_ratio", 1) > 2.5:
            risk += 1
        if features.get("blacklisted", 0) > 0:
            risk += 2
        labels.append(1 if risk >= 2 else 0)
    return np.array(labels)


def _get_model():
    xgb_spec = importlib.util.find_spec("xgboost")
    if xgb_spec:
        from xgboost import XGBClassifier

        return XGBClassifier(
            n_estimators=150,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            random_state=42,
        )
    return RandomForestClassifier(n_estimators=200, max_depth=6, random_state=42)


def _load_pretrained():
    model_path = Path(__file__).resolve().parents[1] / "fraud_model.pkl"
    if not model_path.exists():
        return None
    try:
        with open(model_path, "rb") as handle:
            payload = pickle.load(handle)
        if isinstance(payload, dict) and "model" in payload:
            return payload["model"]
        return payload
    except Exception:
        return None


class SupervisedClassifier:
    def __init__(self) -> None:
        self.model = _get_model()
        self.fitted = False
        self.uses_pretrained = False
        pretrained = _load_pretrained()
        if pretrained is not None:
            self.model = pretrained
            self.fitted = True
            self.uses_pretrained = True

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        if len(X) < 5:
            return
        self.model.fit(X, y)
        self.fitted = True

    def predict(self, target_vector: np.ndarray, X: np.ndarray, feature_dicts: list[dict]) -> float:
        if self.uses_pretrained:
            prob = self.model.predict_proba([target_vector])[0][1]
            return float(max(0.0, min(100.0, prob * 100)))

        y = _build_labels(feature_dicts)
        if len(X) == 0:
            return 30.0
        self.fit(X, y)
        if not self.fitted:
            heuristic = 20 + (target_vector[0] / 12000) * 60
            return float(max(0.0, min(100.0, heuristic)))
        prob = self.model.predict_proba([target_vector])[0][1]
        return float(max(0.0, min(100.0, prob * 100)))
