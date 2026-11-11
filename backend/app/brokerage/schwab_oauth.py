"""Charles Schwab Trader API OAuth token helpers (authorization-code grant)."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import unquote, urlencode

import httpx
from fastapi import HTTPException

SCHWAB_AUTHORIZE_URL = "https://api.schwabapi.com/v1/oauth/authorize"
SCHWAB_TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"


def build_authorize_url(*, app_key: str, callback_url: str, state: str) -> str:
    query = urlencode(
        {
            "client_id": app_key,
            "redirect_uri": callback_url,
            "state": state,
        }
    )
    return f"{SCHWAB_AUTHORIZE_URL}?{query}"


def _basic_auth_header(app_key: str, app_secret: str) -> str:
    raw = f"{app_key}:{app_secret}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _parse_token_response(payload: dict[str, Any]) -> dict[str, Any]:
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    if not isinstance(access_token, str) or not access_token:
        raise HTTPException(
            status_code=502,
            detail={"code": "schwab_token_missing", "message": "Schwab did not return an access token."},
        )
    if not isinstance(refresh_token, str) or not refresh_token:
        raise HTTPException(
            status_code=502,
            detail={"code": "schwab_refresh_missing", "message": "Schwab did not return a refresh token."},
        )
    expires_in = payload.get("expires_in", 1800)
    try:
        seconds = int(expires_in)
    except (TypeError, ValueError):
        seconds = 1800
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(seconds - 30, 60))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": payload.get("token_type", "Bearer"),
        "scope": payload.get("scope"),
        "id_token": payload.get("id_token"),
        "access_expires_at": expires_at.isoformat(),
    }


def exchange_authorization_code(
    *,
    app_key: str,
    app_secret: str,
    code: str,
    callback_url: str,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Exchange the LMS authorization code for access + refresh tokens."""
    decoded = unquote(code.strip())
    headers = {
        "Authorization": _basic_auth_header(app_key, app_secret),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "authorization_code",
        "code": decoded,
        "redirect_uri": callback_url,
    }
    own_client = client is None
    http = client or httpx.Client(timeout=30.0)
    try:
        response = http.post(SCHWAB_TOKEN_URL, headers=headers, data=data)
    finally:
        if own_client:
            http.close()
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "schwab_token_exchange_failed",
                "message": f"Schwab token exchange failed ({response.status_code}).",
            },
        )
    payload = response.json()
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=502,
            detail={"code": "schwab_token_invalid", "message": "Schwab token response was not JSON."},
        )
    return _parse_token_response(payload)


def refresh_access_token(
    *,
    app_key: str,
    app_secret: str,
    refresh_token: str,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Renew access (and refresh) tokens before/after the 30-minute access expiry."""
    headers = {
        "Authorization": _basic_auth_header(app_key, app_secret),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    own_client = client is None
    http = client or httpx.Client(timeout=30.0)
    try:
        response = http.post(SCHWAB_TOKEN_URL, headers=headers, data=data)
    finally:
        if own_client:
            http.close()
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "schwab_refresh_failed",
                "message": f"Schwab token refresh failed ({response.status_code}). Re-authorize in Settings.",
            },
        )
    payload = response.json()
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=502,
            detail={"code": "schwab_token_invalid", "message": "Schwab refresh response was not JSON."},
        )
    return _parse_token_response(payload)
