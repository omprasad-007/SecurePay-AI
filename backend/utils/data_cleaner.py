from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

INVALID_ROWS_PATH = Path(__file__).resolve().parents[1] / "invalid_rows.json"


def _clean_amount(value) -> float | None:
    if pd.isna(value):
        return None
    text = str(value)
    text = re.sub(r"[^0-9.-]", "", text)
    if text in {"", ".", "-", "-."}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def clean_and_validate(df: pd.DataFrame) -> Tuple[pd.DataFrame, list[dict], dict]:
    working = df.copy()
    invalid_rows: list[dict] = []

    required = ["amount", "timestamp"]
    working = working.dropna(subset=[col for col in required if col in working.columns])

    if "amount" in working.columns:
        working["amount"] = working["amount"].apply(_clean_amount)
        invalid_amount = working[working["amount"].isna()]
        for _, row in invalid_amount.iterrows():
            invalid_rows.append({"reason": "invalid_amount", "row": row.to_dict()})
        working = working.dropna(subset=["amount"])

    if "timestamp" in working.columns:
        working["timestamp"] = pd.to_datetime(working["timestamp"], errors="coerce", utc=True)
        invalid_time = working[working["timestamp"].isna()]
        for _, row in invalid_time.iterrows():
            invalid_rows.append({"reason": "invalid_timestamp", "row": row.to_dict()})
        working = working.dropna(subset=["timestamp"])
        working["timestamp"] = working["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    dedupe_cols = [col for col in ["transaction_id", "user_id", "amount", "timestamp"] if col in working.columns]
    before_dedupe = len(working)
    if dedupe_cols:
        working = working.drop_duplicates(subset=dedupe_cols)
    duplicates_removed = before_dedupe - len(working)

    outlier_count = 0
    if "amount" in working.columns and len(working) > 2:
        zscores = np.abs((working["amount"] - working["amount"].mean()) / (working["amount"].std() + 1e-6))
        outlier_count = int((zscores > 3).sum())

    INVALID_ROWS_PATH.write_text(json.dumps(invalid_rows, default=str, indent=2), encoding="utf-8")

    stats = {
        "rows_after_cleaning": len(working),
        "duplicates_removed": duplicates_removed,
        "outlier_count": outlier_count,
        "invalid_rows": len(invalid_rows),
    }
    return working, invalid_rows, stats
