from __future__ import annotations

import argparse
import os
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

CITIES = [
    {"city": "Mumbai", "lat": 19.076, "lon": 72.8777},
    {"city": "Delhi", "lat": 28.7041, "lon": 77.1025},
    {"city": "Bengaluru", "lat": 12.9716, "lon": 77.5946},
    {"city": "Hyderabad", "lat": 17.385, "lon": 78.4867},
    {"city": "Chennai", "lat": 13.0827, "lon": 80.2707},
]

DEVICES = ["DEV-AX21", "DEV-BX99", "DEV-CY88", "DEV-DZ10", "DEV-PX55"]
MERCHANTS = ["Flipkart", "Amazon", "Zomato", "PaytmMall", "IRCTC", "Swiggy", "UnknownWallet"]
BLACKLISTED = {"MERCH99", "RISKY001"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic UPI transactions")
    parser.add_argument("--rows", type=int, default=2000)
    parser.add_argument("--output", type=str, default="data/synthetic_upi.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    random.seed(42)
    np.random.seed(42)

    users = [f"USER{i}" for i in range(1, 9)]
    receivers = [f"MERCH{i}" for i in range(1, 12)] + ["MERCH99", "RISKY001"]

    user_state = {
        user: {
            "device": random.choice(DEVICES),
            "location": random.choice(CITIES),
            "last_time": datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
        }
        for user in users
    }

    rows = []
    for idx in range(args.rows):
        user = random.choice(users)
        receiver = random.choice(receivers)
        state = user_state[user]

        device_change = random.random() < 0.1
        location_change = random.random() < 0.08

        if device_change:
            state["device"] = random.choice(DEVICES)
        if location_change:
            state["location"] = random.choice(CITIES)

        base_amount = np.random.lognormal(mean=7.2, sigma=0.55)
        amount = min(max(base_amount, 120), 50000)

        timestamp = state["last_time"] + timedelta(minutes=random.randint(10, 240))
        state["last_time"] = timestamp

        is_blacklisted = receiver in BLACKLISTED
        is_high_amount = amount > 15000
        is_combo = device_change and amount > 8000
        is_suspicious = is_blacklisted or is_high_amount or is_combo or location_change and amount > 6000
        label = 1 if is_suspicious else 0

        rows.append(
            {
                "id": f"TXN{100000 + idx}",
                "userId": user,
                "receiverId": receiver,
                "amount": round(float(amount), 2),
                "deviceId": state["device"],
                "merchant": random.choice(MERCHANTS),
                "channel": "UPI",
                "ip": f"192.168.1.{random.randint(10, 240)}",
                "location_city": state["location"]["city"],
                "location_lat": state["location"]["lat"],
                "location_lon": state["location"]["lon"],
                "timestamp": timestamp.isoformat() + "Z",
                "label": label,
            }
        )

    df = pd.DataFrame(rows)
    output_path = args.output
    if "\\" in output_path:
        output_path = output_path.replace("\\", "/")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} rows to {output_path}")


if __name__ == "__main__":
    main()
