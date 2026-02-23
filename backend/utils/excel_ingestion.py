from __future__ import annotations

import io
import re
from difflib import get_close_matches
from typing import Dict, Tuple

import pandas as pd

STANDARD_COLUMNS = {
    "transaction_id": ["transaction_id", "txn_id", "transactionid", "id", "txnid"],
    "user_id": ["user_id", "userid", "customer_id", "sender_id", "user"],
    "amount": ["amount", "txn_amt", "value", "transaction_amount", "amt"],
    "timestamp": ["timestamp", "time", "date", "datetime", "txn_time"],
    "merchant": ["merchant", "merchant_name", "payee", "vendor", "receiver"],
    "location": ["location", "city", "geo", "region", "place"],
    "device_id": ["device_id", "device", "deviceid", "fingerprint", "device_hash"],
}


def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def read_excel_or_csv(content: bytes, filename: str) -> pd.DataFrame:
    lower = filename.lower()
    if lower.endswith(".csv"):
        return pd.read_csv(io.BytesIO(content))
    return pd.read_excel(io.BytesIO(content), engine="openpyxl")


def detect_and_map_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str], list[str]]:
    original_columns = list(df.columns)
    normalized = {_normalize_name(col): col for col in original_columns}

    mapping: Dict[str, str] = {}
    missing: list[str] = []

    for standard, aliases in STANDARD_COLUMNS.items():
        found = None
        for alias in aliases:
            if alias in normalized:
                found = normalized[alias]
                break

        if not found:
            candidates = get_close_matches(standard, list(normalized.keys()), n=1, cutoff=0.65)
            if candidates:
                found = normalized[candidates[0]]

        if found:
            mapping[standard] = found
        else:
            missing.append(standard)

    renamed = df.rename(columns={source: target for target, source in mapping.items()})
    return renamed, mapping, missing
