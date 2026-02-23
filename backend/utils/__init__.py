from __future__ import annotations

import logging
import re

logger = logging.getLogger("securepay")


def sanitize_text(value: str) -> str:
    if not value:
        return ""
    value = value.strip()
    return re.sub(r"[^a-zA-Z0-9@_.-]", "", value)


def log_fraud_attempt(message: str) -> None:
    logger.warning(message)
