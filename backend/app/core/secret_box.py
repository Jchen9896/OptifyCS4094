"""Encrypt small JSON payloads for per-user brokerage secrets."""

from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

from app.core.config import Settings, get_settings


def _fernet(settings: Settings | None = None) -> Fernet:
    cfg = settings or get_settings()
    key = cfg.credentials_fernet_key.strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "credentials_key_missing",
                "message": "CREDENTIALS_FERNET_KEY is not configured on the API.",
            },
        )
    try:
        return Fernet(key.encode("utf-8") if isinstance(key, str) else key)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "credentials_key_invalid",
                "message": "CREDENTIALS_FERNET_KEY is not a valid Fernet key.",
            },
        ) from exc


def encrypt_json(payload: dict[str, Any], settings: Settings | None = None) -> str:
    """Return a Fernet token for the JSON object."""
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _fernet(settings).encrypt(raw).decode("utf-8")


def decrypt_json(token: str, settings: Settings | None = None) -> dict[str, Any]:
    """Decrypt a Fernet token back to a JSON object."""
    try:
        raw = _fernet(settings).decrypt(token.encode("utf-8"))
    except InvalidToken as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "credentials_decrypt_failed",
                "message": "Stored brokerage credentials could not be decrypted.",
            },
        ) from exc
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=500,
            detail={
                "code": "credentials_payload_invalid",
                "message": "Stored brokerage credentials have an unexpected shape.",
            },
        )
    return data
