"""Save and read optimization runs for their portfolio owner."""

import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.core.errors import OptimizationRunNotFoundError, PortfolioNotFoundError
from app.models.optimization_run import OptimizationRun
from app.repositories.optimization_run_repository import OptimizationRunRepository
from app.repositories.portfolio_repository import PortfolioRepository
from app.schemas.optimization_run import (
    OptimizationRunCreateRequest,
    OptimizationRunDetailResponse,
    OptimizationRunSummaryResponse,
)


class OptimizationRunService:
    """Apply ownership rules through injected repositories."""

    def __init__(
        self,
        runs: OptimizationRunRepository,
        portfolios: PortfolioRepository,
    ) -> None:
        self._runs = runs
        self._portfolios = portfolios

    def create_run(
        self,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
        request: OptimizationRunCreateRequest,
    ) -> OptimizationRunDetailResponse:
        self._require_owned_portfolio(portfolio_id, user_id)
        row = self._runs.create(
            portfolio_id,
            request.params.model_dump(mode="json"),
            request.result.model_dump(mode="json"),
        )
        return self._to_detail(row)

    def list_runs(
        self,
        portfolio_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        limit: int = 20,
    ) -> list[OptimizationRunSummaryResponse]:
        self._require_owned_portfolio(portfolio_id, user_id)
        return [self._to_summary(row) for row in self._runs.list_for_portfolio(portfolio_id, limit=limit)]

    def get_run(
        self,
        portfolio_id: uuid.UUID,
        run_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> OptimizationRunDetailResponse:
        self._require_owned_portfolio(portfolio_id, user_id)
        row = self._runs.get_for_portfolio(run_id, portfolio_id)
        if row is None:
            raise OptimizationRunNotFoundError()
        return self._to_detail(row)

    def delete_run(
        self,
        portfolio_id: uuid.UUID,
        run_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        self._require_owned_portfolio(portfolio_id, user_id)
        row = self._runs.get_for_portfolio(run_id, portfolio_id)
        if row is None:
            raise OptimizationRunNotFoundError()
        self._runs.delete(row)

    def _require_owned_portfolio(self, portfolio_id: uuid.UUID, user_id: uuid.UUID) -> None:
        if self._portfolios.get_for_user(portfolio_id, user_id) is None:
            raise PortfolioNotFoundError()

    def _to_detail(self, row: OptimizationRun) -> OptimizationRunDetailResponse:
        return OptimizationRunDetailResponse.model_validate(
            {
                "id": row.id,
                "portfolio_id": row.portfolio_id,
                "params": row.params,
                "result": row.result,
                "created_at": row.created_at,
            }
        )

    def _to_summary(self, row: OptimizationRun) -> OptimizationRunSummaryResponse:
        params = row.params or {}
        result = row.result or {}
        return OptimizationRunSummaryResponse(
            id=row.id,
            portfolio_id=row.portfolio_id,
            strategy=str(params.get("strategy") or result.get("strategy") or "unknown"),
            period_start=_as_date(result.get("period_start") or params.get("start_date")),
            period_end=_as_date(result.get("period_end") or params.get("end_date")),
            expected_return=float(result.get("expected_return", 0)),
            volatility=float(result.get("volatility", 0)),
            sharpe_ratio=float(result.get("sharpe_ratio", 0)),
            created_at=row.created_at,
        )


def _as_date(value: object) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return date.fromisoformat(value)
    raise ValueError("Optimization run is missing a period date.")


def create_optimization_run_service(session: Session) -> OptimizationRunService:
    return OptimizationRunService(
        OptimizationRunRepository(session),
        PortfolioRepository(session),
    )
