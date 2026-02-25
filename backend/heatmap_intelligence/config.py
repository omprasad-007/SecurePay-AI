from __future__ import annotations

import os
from dataclasses import dataclass


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class HeatmapSettings:
    db_url: str = os.getenv("HEATMAP_PLUGIN_DB_URL", os.getenv("AUDIT_PLUGIN_DB_URL", "sqlite:///./audit_plugin.db"))
    cache_ttl_seconds: int = int(os.getenv("HEATMAP_CACHE_TTL_SECONDS", "45"))
    max_query_days: int = int(os.getenv("HEATMAP_MAX_QUERY_DAYS", "180"))
    default_limit: int = int(os.getenv("HEATMAP_DEFAULT_LIMIT", "2000"))
    max_limit: int = int(os.getenv("HEATMAP_MAX_LIMIT", "10000"))
    rate_limit_per_minute: int = int(os.getenv("HEATMAP_RATE_LIMIT_PER_MINUTE", "90"))
    predictive_growth_threshold: float = float(os.getenv("HEATMAP_PREDICTIVE_GROWTH_THRESHOLD", "0.25"))
    spike_increase_threshold_pct: float = float(os.getenv("HEATMAP_SPIKE_INCREASE_THRESHOLD_PCT", "40.0"))
    cluster_alert_threshold: int = int(os.getenv("HEATMAP_CLUSTER_ALERT_THRESHOLD", "4"))
    allow_insecure_dev: bool = _bool(os.getenv("ALLOW_INSECURE_DEV"), True)


settings = HeatmapSettings()

