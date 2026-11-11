"""Schwab authorize + callback store tokens in the vault."""

import uuid
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import Header
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models.brokerage_credential  # noqa: F401
from app.api.routes import brokerage_credentials as routes
from app.brokerage.oauth_state import create_oauth_state
from app.core.config import Settings, get_settings
from app.core.current_user import get_current_user_id
from app.core.db import Base, get_db
from app.core.secret_box import decrypt_json
from app.main import create_app
from app.models.brokerage_credential import BrokerageCredential
from app.models.user import User
from app.services.brokerage_credential_service import create_brokerage_credential_service


@pytest.fixture
def api(monkeypatch):
    fernet_key = Fernet.generate_key().decode()
    monkeypatch.setenv("CREDENTIALS_FERNET_KEY", fernet_key)
    monkeypatch.setenv("PUBLIC_API_BASE_URL", "https://127.0.0.1:8000")
    monkeypatch.setenv("FRONTEND_APP_URL", "http://127.0.0.1:5173")
    get_settings.cache_clear()
    settings = Settings(
        credentials_fernet_key=fernet_key,
        public_api_base_url="https://127.0.0.1:8000",
        frontend_app_url="http://127.0.0.1:5173",
    )

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        owner = User(email="owner@example.com", password_hash="test-only")
        session.add(owner)
        session.commit()
        owner_id = owner.id

    def database():
        with Session(engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def handler(request: httpx.Request) -> httpx.Response:
        assert b"grant_type=authorization_code" in request.content
        return httpx.Response(
            200,
            json={
                "expires_in": 1800,
                "token_type": "Bearer",
                "refresh_token": "refresh-xyz",
                "access_token": "access-xyz",
            },
        )

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)

    app = create_app()
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_settings] = lambda: settings

    def current_user(authorization: str = Header(default="")):
        return owner_id

    app.dependency_overrides[get_current_user_id] = current_user

    def service(db=None, settings_dep=None):
        # Used by Depends — recreate each request with shared mock client.
        from fastapi import Depends

        _ = Depends
        return None

    def get_service(db: Session = None):
        return create_brokerage_credential_service(db, settings, http_client)

    from fastapi import Depends

    def override_service(db: Session = Depends(get_db)):
        return create_brokerage_credential_service(db, settings, http_client)

    app.dependency_overrides[routes.get_brokerage_credential_service] = override_service

    with TestClient(app) as client:
        yield client, {"Authorization": "Bearer owner"}, engine, settings, owner_id
    http_client.close()
    engine.dispose()
    get_settings.cache_clear()


def test_authorize_and_callback_vault_tokens(api):
    client, owner, engine, settings, owner_id = api
    saved = client.put(
        "/api/brokerage-credentials/schwab",
        headers=owner,
        json={"app_key": "app-key-42", "app_secret": "app-secret"},
    )
    assert saved.status_code == 200
    assert saved.json()["authorized"] is False
    assert saved.json()["callback_url"].endswith("/api/brokerage-credentials/schwab/callback")

    setup = client.get("/api/brokerage-credentials/schwab/setup")
    assert setup.status_code == 200
    assert setup.json()["callback_url"] == settings.schwab_oauth_callback_url

    authorize = client.post("/api/brokerage-credentials/schwab/authorize", headers=owner)
    assert authorize.status_code == 200
    authorize_url = authorize.json()["authorize_url"]
    query = parse_qs(urlparse(authorize_url).query)
    state = query["state"][0]
    assert query["client_id"] == ["app-key-42"]

    callback = client.get(
        "/api/brokerage-credentials/schwab/callback",
        params={"code": "auth-code", "state": state},
        follow_redirects=False,
    )
    assert callback.status_code == 302
    assert callback.headers["location"].startswith("http://127.0.0.1:5173/settings?schwab=connected")

    status = client.get("/api/brokerage-credentials", headers=owner).json()
    assert status[0]["authorized"] is True

    with Session(engine) as session:
        row = session.scalar(select(BrokerageCredential).where(BrokerageCredential.user_id == owner_id))
        secrets = decrypt_json(row.secrets_ciphertext, settings)
        assert secrets["access_token"] == "access-xyz"
        assert secrets["refresh_token"] == "refresh-xyz"
        assert secrets["app_key"] == "app-key-42"


def test_callback_rejects_foreign_state(api):
    client, owner, _engine, settings, _owner_id = api
    client.put(
        "/api/brokerage-credentials/schwab",
        headers=owner,
        json={"app_key": "k", "app_secret": "s"},
    )
    foreign = create_oauth_state(uuid.uuid4(), settings)
    response = client.get(
        "/api/brokerage-credentials/schwab/callback",
        params={"code": "x", "state": foreign},
        follow_redirects=False,
    )
    assert response.status_code == 404
