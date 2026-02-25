from __future__ import annotations

import os
from dataclasses import dataclass


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class AuditPluginSettings:
    db_url: str = os.getenv("AUDIT_PLUGIN_DB_URL", "sqlite:///./audit_plugin.db")
    max_upload_mb: int = int(os.getenv("AUDIT_PLUGIN_MAX_UPLOAD_MB", "10"))
    smtp_host: str = os.getenv("AUDIT_PLUGIN_SMTP_HOST", "")
    smtp_port: int = int(os.getenv("AUDIT_PLUGIN_SMTP_PORT", "587"))
    smtp_user: str = os.getenv("AUDIT_PLUGIN_SMTP_USER", "")
    smtp_password: str = os.getenv("AUDIT_PLUGIN_SMTP_PASSWORD", "")
    smtp_sender: str = os.getenv("AUDIT_PLUGIN_SMTP_SENDER", "")
    smtp_tls: bool = _bool(os.getenv("AUDIT_PLUGIN_SMTP_TLS"), True)


settings = AuditPluginSettings()
