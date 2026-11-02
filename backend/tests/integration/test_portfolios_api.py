"""API tests for portfolio update and delete. A fake service replaces the database."""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.routes.portfolios import get_portfolio_service
from app.core.errors import (
    DuplicatePortfolioNameError,
    InvalidPortfolioNameError,
    PortfolioNotFoundError,
)
from app.main import create_app
from app.models.portfolio import Portfolio


class FakePortfolioService:
    def __init__(self, portfolio=None, error=None):
        self.portfolio = portfolio
        self.error = error
        self.deleted = False

    def update_portfolio(self, _portfolio_id, _user_id, _name):
        if self.error:
            raise self.error
        return self.portfolio

    def delete_portfolio(self, _portfolio_id, _user_id):
        if self.error:
            raise self.error
        self.deleted = True


def client_for(service: FakePortfolioService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_portfolio_service] = lambda: service
    return TestClient(app)


def sample_portfolio() -> Portfolio:
    return Portfolio(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        user_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        name="Growth",
        created_at=datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc),
    )


PORTFOLIO_URL = "/api/portfolios/11111111-1111-1111-1111-111111111111"
USER_QUERY = {"user_id": "22222222-2222-2222-2222-222222222222"}


def test_update_returns_the_renamed_portfolio():
    response = client_for(FakePortfolioService(sample_portfolio())).patch(
        PORTFOLIO_URL,
        params=USER_QUERY,
        json={"name": "Growth"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "11111111-1111-1111-1111-111111111111",
        "user_id": "22222222-2222-2222-2222-222222222222",
        "name": "Growth",
        "created_at": "2026-10-28T12:00:00Z",
    }


def test_delete_returns_no_content():
    service = FakePortfolioService()
    response = client_for(service).delete(PORTFOLIO_URL, params=USER_QUERY)

    assert response.status_code == 204
    assert response.content == b""
    assert service.deleted is True


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (PortfolioNotFoundError(), 404),
        (InvalidPortfolioNameError(), 422),
        (DuplicatePortfolioNameError(), 409),
    ],
)
def test_update_failure_has_its_own_code_and_message(error, status_code):
    response = client_for(FakePortfolioService(error=error)).patch(
        PORTFOLIO_URL,
        params=USER_QUERY,
        json={"name": "Growth"},
    )

    assert response.status_code == status_code
    assert response.json() == {"detail": {"code": error.code, "message": error.message}}


def test_delete_failure_has_its_own_code_and_message():
    error = PortfolioNotFoundError()
    response = client_for(FakePortfolioService(error=error)).delete(PORTFOLIO_URL, params=USER_QUERY)

    assert response.status_code == 404
    assert response.json() == {"detail": {"code": error.code, "message": error.message}}
