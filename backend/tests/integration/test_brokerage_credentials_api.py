"""BYOK credential vault HTTP routes never leak secrets."""

import uuid

import pytest
from cryptography.fernet import Fernet
from fastapi import Header
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models.brokerage_credential  # noqa: F401
from app.core.config import Settings, get_settings
from app.core.current_user import get_current_user_id
from app.core.db import Base, get_db
from app.core.secret_box import decrypt_json
from app.main import create_app
from app.models.brokerage_credential import BrokerageCredential
from app.models.user import User


@pytest.fixture
def api(monkeypatch):
    fernet_key = Fernet.generate_key().decode()
    monkeypatch.setenv("CREDENTIALS_FERNET_KEY", fernet_key)
    monkeypatch.setenv("PUBLIC_API_BASE_URL", "https://127.0.0.1:8000")
    monkeypatch.setenv("FRONTEND_APP_URL", "http://127.0.0.1:5173")
    get_settings.cache_clear()

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        owner = User(email="owner@example.com", password_hash="test-only")
        outsider = User(email="outsider@example.com", password_hash="test-only")
        session.add_all([owner, outsider])
        session.commit()
        owner_id = owner.id
        outsider_id = outsider.id

    def database():
        with Session(engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app = create_app()
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_settings] = lambda: Settings(
        credentials_fernet_key=fernet_key,
        public_api_base_url="https://127.0.0.1:8000",
        frontend_app_url="http://127.0.0.1:5173",
    )

    def current_user(authorization: str = Header(default="")):
        return outsider_id if authorization == "Bearer outsider" else owner_id

    app.dependency_overrides[get_current_user_id] = current_user
    with TestClient(app) as client:
        yield client, {"Authorization": "Bearer owner"}, {"Authorization": "Bearer outsider"}, engine, fernet_key
    engine.dispose()
    get_settings.cache_clear()


def test_put_list_delete_never_returns_secrets(api):
    client, owner, outsider, engine, fernet_key = api
    body = {
        "app_key": "schwab-app-key-9999",
        "app_secret": "schwab-app-secret",
    }
    created = client.put("/api/brokerage-credentials/schwab", headers=owner, json=body)
    assert created.status_code == 200
    saved = created.json()
    assert saved["provider"] == "schwab"
    assert saved["app_key_hint"] == "9999"
    assert saved["callback_url"].endswith("/api/brokerage-credentials/schwab/callback")
    assert saved["authorized"] is False
    assert "app_key" not in saved
    assert "app_secret" not in saved
    assert "secrets_ciphertext" not in saved

    listing = client.get("/api/brokerage-credentials", headers=owner)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["app_key_hint"] == "9999"
    assert "app_secret" not in listing.json()[0]

    assert client.get("/api/brokerage-credentials", headers=outsider).json() == []

    with Session(engine) as session:
        row = session.scalar(select(BrokerageCredential))
        assert row is not None
        assert "schwab-app-secret" not in row.secrets_ciphertext
        secrets = decrypt_json(row.secrets_ciphertext, Settings(credentials_fernet_key=fernet_key))
        assert secrets == {"app_key": "schwab-app-key-9999", "app_secret": "schwab-app-secret"}

    deleted = client.delete("/api/brokerage-credentials/schwab", headers=owner)
    assert deleted.status_code == 204
    assert client.get("/api/brokerage-credentials", headers=owner).json() == []
    assert client.delete("/api/brokerage-credentials/schwab", headers=owner).status_code == 404


def test_upsert_uses_canonical_https_callback(api):
    client, owner, _outsider, _engine, _key = api
    response = client.put(
        "/api/brokerage-credentials/schwab",
        headers=owner,
        json={"app_key": "k", "app_secret": "s", "callback_url": "http://ignored.example"},
    )
    assert response.status_code == 200
    assert response.json()["callback_url"].startswith("https://")
