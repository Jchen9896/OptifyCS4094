import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models.brokerage_credential  # noqa: F401
from app.core.config import Settings
from app.core.db import Base
from app.core.secret_box import encrypt_json
from app.models.brokerage_credential import BrokerageCredential
from app.models.user import User
from app.repositories.brokerage_credential_repository import BrokerageCredentialRepository
from app.schemas.trade import SubmitSchwabOrdersRequest, TradeOrderLeg
from app.services.brokerage_credential_service import BrokerageCredentialService
from app.services.trade_service import TradeService


@pytest.fixture
def trade_env(tmp_path):
    fernet_key = Fernet.generate_key().decode()
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
        owner = User(email="trader@example.com", password_hash="test-only")
        session.add(owner)
        session.commit()
        owner_id = owner.id
        secrets = {
            "app_key": "key",
            "app_secret": "secret",
            "access_token": "access-live",
            "refresh_token": "refresh-live",
            "access_expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }
        session.add(
            BrokerageCredential(
                user_id=owner_id,
                provider="schwab",
                callback_url=settings.schwab_oauth_callback_url,
                app_key_hint="key",
                secrets_ciphertext=encrypt_json(secrets, settings),
            )
        )
        session.commit()

    return engine, settings, owner_id


def test_submit_schwab_orders_places_whole_share_legs(trade_env):
    engine, settings, owner_id = trade_env
    seen: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/accounts/accountNumbers"):
            return httpx.Response(
                200,
                json=[{"accountNumber": "9999", "hashValue": "hash-1"}],
            )
        if request.method == "POST" and "/orders" in request.url.path:
            body = request.read()
            seen.append(body)
            return httpx.Response(
                201,
                headers={"Location": "https://api.schwabapi.com/trader/v1/accounts/hash-1/orders/42"},
            )
        return httpx.Response(500, json={"message": "unexpected"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with Session(engine) as session:
        credentials = BrokerageCredentialService(
            BrokerageCredentialRepository(session),
            settings,
            client,
        )
        service = TradeService(credentials, client)
        response = service.submit_schwab_orders(
            owner_id,
            SubmitSchwabOrdersRequest(
                account_hash="hash-1",
                orders=[
                    TradeOrderLeg(symbol="aapl", side="buy", quantity=5),
                    TradeOrderLeg(symbol="MSFT", side="sell", quantity=2),
                ],
            ),
        )

    assert response.account_number == "9999"
    assert [row.status for row in response.results] == ["accepted", "accepted"]
    assert response.results[0].order_id == "42"
    assert len(seen) == 2
    assert b'"quantity":5' in seen[0]
    assert b'"SELL"' in seen[1]
