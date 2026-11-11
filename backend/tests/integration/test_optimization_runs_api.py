"""API tests for optimization run routes. A fake service replaces the database."""

import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.routes.optimization_runs import get_optimization_run_service
from app.core.current_user import get_current_user_id
from app.core.errors import OptimizationRunNotFoundError, PortfolioNotFoundError
from app.main import create_app
from app.schemas.optimization import EquityCurvePointSchema, OptimizationResult
from app.schemas.optimization_run import (
    OptimizationRunDetailResponse,
    OptimizationRunParams,
    OptimizationRunSummaryResponse,
)


USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
PORTFOLIO_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
RUN_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
BASE = f"/api/portfolios/{PORTFOLIO_ID}/optimization-runs"


def sample_detail() -> OptimizationRunDetailResponse:
    return OptimizationRunDetailResponse(
        id=RUN_ID,
        portfolio_id=PORTFOLIO_ID,
        params=OptimizationRunParams(
            tickers=["AAPL", "MSFT"],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 1),
            strategy="min_variance",
            max_weight=0.6,
            risk_free_rate=0.04,
            initial_capital=10000,
            current_weights=[0.5, 0.5],
        ),
        result=OptimizationResult(
            strategy="min_variance",
            weights={"AAPL": 0.4, "MSFT": 0.6},
            expected_return=0.08,
            volatility=0.12,
            sharpe_ratio=0.33,
            current_expected_return=0.07,
            current_volatility=0.14,
            current_sharpe_ratio=0.21,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 6, 1),
            assumptions=["sample"],
            initial_capital=10000,
            equity_curve=[
                EquityCurvePointSchema(
                    date=date(2025, 1, 2),
                    current_value=10000,
                    optimized_value=10020,
                )
            ],
        ),
        created_at=datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc),
    )


class FakeOptimizationRunService:
    def __init__(self, detail=None, rows=None, error=None):
        self.detail = detail
        self.rows = rows or []
        self.error = error
        self.created = None

    def create_run(self, portfolio_id, user_id, request):
        if self.error:
            raise self.error
        self.created = (portfolio_id, user_id, request)
        return self.detail

    def list_runs(self, portfolio_id, user_id, *, limit=20):
        if self.error:
            raise self.error
        return self.rows[:limit]

    def get_run(self, portfolio_id, run_id, user_id):
        if self.error:
            raise self.error
        return self.detail


def client_for(service: FakeOptimizationRunService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_optimization_run_service] = lambda: service
    app.dependency_overrides[get_current_user_id] = lambda: USER_ID
    return TestClient(app)


def test_create_returns_the_saved_run():
    detail = sample_detail()
    service = FakeOptimizationRunService(detail=detail)
    response = client_for(service).post(
        BASE,
        json={
            "params": {
                "tickers": ["AAPL", "MSFT"],
                "start_date": "2025-01-01",
                "end_date": "2025-06-01",
                "strategy": "min_variance",
                "max_weight": 0.6,
                "risk_free_rate": 0.04,
                "initial_capital": 10000,
                "current_weights": [0.5, 0.5],
            },
            "result": detail.result.model_dump(mode="json"),
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == str(RUN_ID)
    assert body["result"]["weights"]["MSFT"] == 0.6
    assert service.created[0] == PORTFOLIO_ID
    assert service.created[1] == USER_ID


def test_list_returns_summaries():
    rows = [
        OptimizationRunSummaryResponse(
            id=RUN_ID,
            portfolio_id=PORTFOLIO_ID,
            strategy="min_variance",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 6, 1),
            expected_return=0.08,
            volatility=0.12,
            sharpe_ratio=0.33,
            created_at=datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc),
        )
    ]
    response = client_for(FakeOptimizationRunService(rows=rows)).get(BASE)

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(RUN_ID),
            "portfolio_id": str(PORTFOLIO_ID),
            "strategy": "min_variance",
            "period_start": "2025-01-01",
            "period_end": "2025-06-01",
            "expected_return": 0.08,
            "volatility": 0.12,
            "sharpe_ratio": 0.33,
            "created_at": "2026-11-11T12:00:00Z",
        }
    ]


def test_read_returns_one_run():
    response = client_for(FakeOptimizationRunService(detail=sample_detail())).get(f"{BASE}/{RUN_ID}")

    assert response.status_code == 200
    assert response.json()["id"] == str(RUN_ID)


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (PortfolioNotFoundError(), 404, "portfolio_not_found"),
        (OptimizationRunNotFoundError(), 404, "optimization_run_not_found"),
    ],
)
def test_read_failure_has_its_own_code(error, status_code, code):
    response = client_for(FakeOptimizationRunService(error=error)).get(f"{BASE}/{RUN_ID}")

    assert response.status_code == status_code
    assert response.json() == {"detail": {"code": code, "message": error.message}}
