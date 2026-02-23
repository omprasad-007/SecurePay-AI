from __future__ import annotations

import argparse
import os
import pickle
import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from models.fraud_pipeline import FEATURE_ORDER, build_feature_dict, feature_vector
from models.supervised import _get_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train supervised fraud model")
    parser.add_argument("--input", type=str, default="data/synthetic_upi.csv")
    parser.add_argument("--output", type=str, default=str(PROJECT_ROOT / "fraud_model.pkl"))
    return parser.parse_args()


def _row_to_tx(row: pd.Series) -> dict:
    return {
        "id": row["id"],
        "userId": row["userId"],
        "receiverId": row["receiverId"],
        "amount": float(row["amount"]),
        "deviceId": row["deviceId"],
        "merchant": row.get("merchant", "Unknown"),
        "channel": row.get("channel", "UPI"),
        "ip": row.get("ip", "0.0.0.0"),
        "location": {
            "city": row.get("location_city", "Unknown"),
            "lat": float(row.get("location_lat", 0.0)),
            "lon": float(row.get("location_lon", 0.0)),
        },
        "timestamp": row["timestamp"],
    }


def main() -> None:
    args = parse_args()
    df = pd.read_csv(args.input)
    df = df.sort_values("timestamp")

    history = []
    X = []
    y = []

    for _, row in df.iterrows():
        tx = _row_to_tx(row)
        features = build_feature_dict(tx, history)
        X.append(feature_vector(features))
        y.append(int(row.get("label", 0)))
        history.append(tx)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = _get_model()
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else preds

    accuracy = accuracy_score(y_test, preds)
    try:
        auc = roc_auc_score(y_test, probs)
    except ValueError:
        auc = 0.0

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "wb") as handle:
        pickle.dump({"model": model, "feature_order": FEATURE_ORDER}, handle)

    print(f"Saved model to {args.output}")
    print(f"Accuracy: {accuracy:.3f} | AUC: {auc:.3f}")


if __name__ == "__main__":
    main()
