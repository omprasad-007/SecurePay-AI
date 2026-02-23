from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest


def _synthesize_history(X: np.ndarray, feature_dim: int, target_length: int = 60) -> np.ndarray:
    if X.size == 0:
        base = np.random.normal(loc=0.0, scale=1.0, size=(target_length, feature_dim))
        return base
    if len(X) >= target_length:
        return X
    padding = np.random.normal(loc=X.mean(axis=0), scale=X.std(axis=0) + 1e-3, size=(target_length - len(X), X.shape[1]))
    return np.vstack([X, padding])


class IsolationForestAnomaly:
    def __init__(self) -> None:
        self.model = IsolationForest(
            n_estimators=200,
            contamination=0.1,
            random_state=42,
        )

    def score(self, target_vector: np.ndarray, history_vectors: np.ndarray) -> float:
        X = _synthesize_history(history_vectors, feature_dim=target_vector.shape[0], target_length=80)
        self.model.fit(X)
        raw_score = self.model.decision_function([target_vector])[0]
        scaled = (0.5 - raw_score) * 100
        return float(max(0.0, min(100.0, scaled)))
