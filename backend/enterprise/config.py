from __future__ import annotations

import os
from dataclasses import dataclass


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    app_name: str = os.getenv("ENTERPRISE_APP_NAME", "SecurePay AI Enterprise")
    api_prefix: str = os.getenv("ENTERPRISE_API_PREFIX", "")

    database_url: str = os.getenv(
        "ENTERPRISE_DATABASE_URL",
        "postgresql+psycopg2://securepay:securepay@localhost:5432/securepay_enterprise",
    )

    jwt_secret: str = os.getenv("ENTERPRISE_JWT_SECRET", "change-this-secret")
    jwt_algorithm: str = os.getenv("ENTERPRISE_JWT_ALGO", "HS256")
    access_token_minutes: int = int(os.getenv("ENTERPRISE_ACCESS_TOKEN_MIN", "30"))
    refresh_token_days: int = int(os.getenv("ENTERPRISE_REFRESH_TOKEN_DAYS", "7"))

    frontend_origin: str = os.getenv("ENTERPRISE_FRONTEND_ORIGIN", "http://localhost:5173")

    allow_insecure_dev: bool = _bool(os.getenv("ALLOW_INSECURE_DEV"), True)
    firebase_project_id: str | None = os.getenv("FIREBASE_PROJECT_ID")
    firebase_private_key: str | None = os.getenv("FIREBASE_PRIVATE_KEY")
    firebase_client_email: str | None = os.getenv("FIREBASE_CLIENT_EMAIL")

    request_limit_per_minute: int = int(os.getenv("ENTERPRISE_RATE_LIMIT", "120"))


settings = Settings()
