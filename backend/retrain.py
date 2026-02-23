from __future__ import annotations

import argparse
import json
import os
import pickle
from pathlib import Path

import pandas as pd

from models.supervised import _get_model
from models.fraud_pipeline import FEATURE_ORDER, build_feature_dict, feature_vector

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEEDBACK_PATH = PROJECT_ROOT / "feedback.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate weekly retraining with feedback")
    parser.add_argument("--data", type=str, default=str(PROJECT_ROOT / "data" / "synthetic_upi.csv"))
    parser.add_argument("--output", type=str, default=str(PROJECT_ROOT / "fraud_model.pkl"))
    return parser.parse_args()


def load_feedback() -> list[dict]:
    if not FEEDBACK_PATH.exists():
        return []
    try:
        with open(FEEDBACK_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError:
        return []


def main() -> None:
    args = parse_args()
    data_path = Path(args.data)

    if not data_path.exists():
        print(f"Dataset not found at {data_path}. Generate synthetic data first.")
        return

    df = pd.read_csv(data_path)
    df = df.sort_values("timestamp")

    feedback = load_feedback()
    feedback_map = {item.get("transaction_id"): 1 if item.get("label") == "fraud" else 0 for item in feedback}

    history: list[dict] = []
    X = []
    y = []

    for _, row in df.iterrows():
        tx = {
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
        features = build_feature_dict(tx, history)
        X.append(feature_vector(features))
        label = feedback_map.get(tx["id"], int(row.get("label", 0)))
        y.append(label)
        history.append(tx)

    model = _get_model()
    model.fit(X, y)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "wb") as handle:
        pickle.dump({"model": model, "feature_order": FEATURE_ORDER}, handle)

    print(f"Retrained model saved to {args.output} using {len(feedback)} feedback entries")


if __name__ == "__main__":
    main()
