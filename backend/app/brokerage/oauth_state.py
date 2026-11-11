"""Signed OAuth state for Schwab callback (binds code exchange to a user)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app.core.config import Settings
from app.core.secret_box import decrypt_json, encrypt_json

STATE_TTL = timedelta(minutes=15)


def create_oauth_state(user_id: uuid.UUID, settings: Settings) -> str:
    payload = {
        "uid": str(user_id),
        "exp": (datetime.now(timezone.utc) + STATE_TTL).isoformat(),
        "provider": "schwab",
    }
    return encrypt_json(payload, settings)


def verify_oauth_state(state: str, settings: Settings) -> uuid.UUID:
    if not state or not state.strip():
        raise HTTPException(
            status_code=400,
            detail={"code": "oauth_state_missing", "message": "OAuth state is missing."},
        )
    payload = decrypt_json(state.strip(), settings)
    if payload.get("provider") != "schwab":
        raise HTTPException(
            status_code=400,
            detail={"code": "oauth_state_invalid", "message": "OAuth state is invalid."},
        )
    exp_raw = payload.get("exp")
    uid_raw = payload.get("uid")
    if not isinstance(exp_raw, str) or not isinstance(uid_raw, str):
        raise HTTPException(
            status_code=400,
            detail={"code": "oauth_state_invalid", "message": "OAuth state is invalid."},
        )
    try:
        exp = datetime.fromisoformat(exp_raw)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        user_id = uuid.UUID(uid_raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "oauth_state_invalid", "message": "OAuth state is invalid."},
        ) from exc
    if exp < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail={"code": "oauth_state_expired", "message": "OAuth state expired. Start connect again."},
        )
    return user_id
