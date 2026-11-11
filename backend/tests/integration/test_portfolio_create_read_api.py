"""HTTP create/read round trips with injected database and ticker validation."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes.portfolios import get_portfolio_service
from app.core.db import Base, get_db
from app.core.current_user import get_current_user_id
from app.core.errors import MarketDataUnavailableError
from app.main import create_app
from app.market_data.base import StockInfo
from app.models.portfolio import Portfolio
from app.models.stock import Stock
from app.models.user import User
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.stock_repository import StockRepository
from app.services.portfolio_service import PortfolioService


class Tickers:
    def validate_ticker(self, symbol):
        if symbol == "FAIL":
            raise MarketDataUnavailableError()
        return StockInfo(symbol=symbol, name="Apple Inc.", currency="USD", exchange="NMS", quote_type="EQUITY")


@pytest.fixture
def api():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        owner = User(email="owner@example.com", password_hash="test-only")
        session.add(owner)
        session.commit()
        user_id = str(owner.id)

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
    outsider_id = uuid.uuid4()
    def authenticated_user(authorization: str = ""):
        return outsider_id if authorization == "Bearer outsider" else uuid.UUID(user_id)
    from fastapi import Header
    def current_user(authorization: str = Header(default="")):
        return authenticated_user(authorization)
    app.dependency_overrides[get_current_user_id] = current_user

    def service(db):
        return PortfolioService(PortfolioRepository(db), stock_service=Tickers(), stock_repository=StockRepository(db))

    # Retain request session injection while replacing only the external provider.
    from fastapi import Depends

    def get_service(db=Depends(get_db)):
        return service(db)

    app.dependency_overrides[get_portfolio_service] = get_service
    with TestClient(app) as client:
        yield client, {"Authorization": "Bearer owner"}, engine
    engine.dispose()


def payload(name="Core"):
    return {"name": name, "holdings": [{"symbol": " aapl ", "quantity": "10.5"}], "setup": {
        "initial_capital": 1050, "start_date": "2026-01-01", "end_date": "2026-02-01",
        "strategy": "min_variance", "max_weight": 1, "risk_free_rate": 0.04,
        "weights": {"AAPL": 100}, "reference_prices": {"AAPL": 100},
    }}


def test_create_list_and_detail_survive_separate_requests(api):
    client, owner, _engine = api
    response = client.post("/api/portfolios", headers=owner, json=payload(" Core "))
    assert response.status_code == 201
    saved = response.json()
    assert saved["name"] == "Core"
    assert saved["holdings"][0] == {"symbol": "AAPL", "name": "Apple Inc.", "quantity": "10.5"}
    expected_setup = {
        **payload()["setup"],
        "target_return": None,
        "target_volatility": None,
        "quote_types": None,
    }
    assert saved["setup"] == expected_setup
    read = client.get(f'/api/portfolios/{saved["id"]}', headers=owner)
    assert read.status_code == 200
    assert read.json()["setup"] == saved["setup"]
    assert float(read.json()["holdings"][0]["quantity"]) == 10.5
    listing = client.get("/api/portfolios", headers=owner)
    assert listing.status_code == 200
    assert [row["id"] for row in listing.json()] == [saved["id"]]
    outsider = {"Authorization": "Bearer outsider"}
    assert client.get("/api/portfolios", headers=outsider).json() == []
    hidden = client.get(f'/api/portfolios/{saved["id"]}', headers=outsider)
    missing = client.get(f"/api/portfolios/{uuid.uuid4()}", headers=owner)
    assert hidden.status_code == missing.status_code == 404
    assert hidden.json() == missing.json()


def test_create_errors_and_rollback(api):
    client, owner, engine = api
    assert client.post("/api/portfolios", headers=owner, json=payload()).status_code == 201
    duplicate = client.post("/api/portfolios", headers=owner, json=payload())
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "duplicate_portfolio_name"
    blank = client.post("/api/portfolios", headers=owner, json={"name": "  "})
    assert blank.status_code == 422
    assert blank.json()["detail"]["code"] == "invalid_portfolio_name"
    failure = client.post("/api/portfolios", headers=owner, json={"name": "Broken", "holdings": [{"symbol": "FAIL", "quantity": 1}]})
    assert failure.status_code == 503
    assert failure.json()["detail"]["code"] == "market_data_unavailable"
    with Session(engine) as session:
        assert [row.name for row in session.scalars(select(Portfolio))] == ["Core"]
        assert len(session.scalars(select(Stock)).all()) == 1


def test_invalid_payload_and_missing_setup(api):
    client, owner, _engine = api
    bad = payload()
    bad["holdings"][0]["quantity"] = "0.0000001"
    assert client.post("/api/portfolios", headers=owner, json=bad).status_code == 422
    saved = client.post("/api/portfolios", headers=owner, json={"name": "Empty"})
    assert saved.status_code == 201
    assert saved.json()["setup"] is None
    assert saved.json()["holdings"] == []


@pytest.mark.parametrize(("strategy", "expected", "targets"), [
    ("min_variance", "min_variance", {}),
    ("max_sharpe", "max_sharpe", {}),
    ("target_return", "target_return", {"target_return": 0.08}),
    ("target_risk", "target_risk", {"target_volatility": 0.12}),
    ("minvar", "min_variance", {}),
    ("mvo", "min_variance", {}),
])
def test_save_and_read_keep_current_strategy_names(api, strategy, expected, targets):
    client, owner, _engine = api
    body = payload()
    body["setup"]["strategy"] = strategy
    body["setup"].update(targets)
    created = client.post("/api/portfolios", headers=owner, json=body)
    assert created.status_code == 201
    assert created.json()["setup"]["strategy"] == expected
    saved_id = created.json()["id"]
    read = client.get(f"/api/portfolios/{saved_id}", headers=owner)
    assert read.status_code == 200
    assert read.json()["setup"]["strategy"] == expected
