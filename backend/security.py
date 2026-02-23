from __future__ import annotations

import os
from typing import Any

import firebase_admin
from firebase_admin import auth, credentials
from fastapi import Header, HTTPException, status


firebase_ready = False


def _init_firebase() -> None:
    global firebase_ready
    if firebase_ready or firebase_admin._apps:
        firebase_ready = True
        return

    project_id = os.getenv("FIREBASE_PROJECT_ID")
    private_key = os.getenv("FIREBASE_PRIVATE_KEY")
    client_email = os.getenv("FIREBASE_CLIENT_EMAIL")

    if not (project_id and private_key and client_email):
        return

    private_key = private_key.replace("\\n", "\n")
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": project_id,
        "private_key": private_key,
        "client_email": client_email,
        "token_uri": "https://oauth2.googleapis.com/token",
    })
    firebase_admin.initialize_app(cred)
    firebase_ready = True


async def get_current_user(
    authorization: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
) -> dict[str, Any]:
    if os.getenv("ALLOW_INSECURE_DEV", "true").lower() == "true":
        return {"uid": "dev", "role": x_user_role or "Admin"}

    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")

    token = authorization.replace("Bearer", "").strip()
    _init_firebase()

    if not firebase_ready:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Firebase not configured")

    try:
        decoded = auth.verify_id_token(token)
        if x_user_role:
            decoded["role"] = x_user_role
        return decoded
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
