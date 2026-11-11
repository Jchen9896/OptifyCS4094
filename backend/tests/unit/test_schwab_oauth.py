"""Schwab OAuth URL + token helpers."""

from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException

from app.brokerage.oauth_state import create_oauth_state, verify_oauth_state
from app.brokerage.schwab_oauth import build_authorize_url, exchange_authorization_code, refresh_access_token
from app.core.config import Settings
import uuid


@pytest.fixture
def settings() -> Settings:
    return Settings(credentials_fernet_key=Fernet.generate_key().decode())


def test_build_authorize_url_includes_state():
    url = build_authorize_url(
        app_key="key123",
        callback_url="https://127.0.0.1:8000/api/brokerage-credentials/schwab/callback",
        state="signed-state",
    )
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert parsed.netloc == "api.schwabapi.com"
    assert query["client_id"] == ["key123"]
    assert query["state"] == ["signed-state"]


def test_oauth_state_round_trip(settings: Settings):
    user_id = uuid.uuid4()
    state = create_oauth_state(user_id, settings)
    assert verify_oauth_state(state, settings) == user_id


def test_exchange_authorization_code_decodes_and_stores_expiry():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/oauth/token")
        body = request.content.decode()
        assert "grant_type=authorization_code" in body
        assert "abc@def" in body or "abc%40def" in body
        return httpx.Response(
            200,
            json={
                "expires_in": 1800,
                "token_type": "Bearer",
                "scope": "api",
                "refresh_token": "refresh-1",
                "access_token": "access-1",
            },
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        tokens = exchange_authorization_code(
            app_key="k",
            app_secret="s",
            code="abc%40def",
            callback_url="https://127.0.0.1/callback",
            client=client,
        )
    assert tokens["access_token"] == "access-1"
    assert tokens["refresh_token"] == "refresh-1"
    expires = datetime.fromisoformat(tokens["access_expires_at"])
    assert expires.tzinfo is not None
    assert expires > datetime.now(timezone.utc)


def test_refresh_access_token_failure():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid"})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        with pytest.raises(HTTPException) as caught:
            refresh_access_token(app_key="k", app_secret="s", refresh_token="r", client=client)
    assert caught.value.status_code == 502
