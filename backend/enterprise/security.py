from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from .config import settings


@dataclass(slots=True)
class TokenPayload:
    sub: str
    role: str
    organization_id: str
    token_type: str


def hash_password(password: str) -> str:
    import bcrypt

    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    import bcrypt

    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _encode_token(payload: dict[str, Any], expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    to_encode = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str, role: str, organization_id: str) -> str:
    return _encode_token(
        {
            "sub": user_id,
            "role": role,
            "organization_id": organization_id,
            "token_type": "access",
        },
        timedelta(minutes=settings.access_token_minutes),
    )


def create_refresh_token(user_id: str, role: str, organization_id: str) -> str:
    return _encode_token(
        {
            "sub": user_id,
            "role": role,
            "organization_id": organization_id,
            "token_type": "refresh",
        },
        timedelta(days=settings.refresh_token_days),
    )


def decode_token(token: str) -> TokenPayload:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return TokenPayload(
        sub=str(payload["sub"]),
        role=str(payload.get("role", "VIEWER")),
        organization_id=str(payload.get("organization_id", "")),
        token_type=str(payload.get("token_type", "access")),
    )


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def verify_google_id_token(google_id_token: str) -> dict[str, Any]:
    if settings.allow_insecure_dev and os.getenv("ENTERPRISE_SKIP_FIREBASE", "false").lower() == "true":
        return {"email": google_id_token, "name": None}

    try:
        import firebase_admin
        from firebase_admin import auth, credentials

        if not firebase_admin._apps:
            if settings.firebase_project_id and settings.firebase_private_key and settings.firebase_client_email:
                cred = credentials.Certificate(
                    {
                        "type": "service_account",
                        "project_id": settings.firebase_project_id,
                        "private_key": settings.firebase_private_key.replace("\\n", "\n"),
                        "client_email": settings.firebase_client_email,
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                )
                firebase_admin.initialize_app(cred)

        decoded = auth.verify_id_token(google_id_token)
        return {
            "email": decoded.get("email"),
            "name": decoded.get("name"),
            "uid": decoded.get("uid"),
        }
    except Exception as exc:
        raise ValueError("Invalid Google ID token") from exc
