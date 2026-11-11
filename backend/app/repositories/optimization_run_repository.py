"""Persist optimization runs through an injected session."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.optimization_run import OptimizationRun


class OptimizationRunRepository:
    """Create and read runs for one portfolio."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, portfolio_id: uuid.UUID, params: dict, result: dict) -> OptimizationRun:
        row = OptimizationRun(portfolio_id=portfolio_id, params=params, result=result)
        self._session.add(row)
        self._session.flush()
        return row

    def list_for_portfolio(self, portfolio_id: uuid.UUID, *, limit: int = 20) -> list[OptimizationRun]:
        return list(
            self._session.scalars(
                select(OptimizationRun)
                .where(OptimizationRun.portfolio_id == portfolio_id)
                .order_by(OptimizationRun.created_at.desc(), OptimizationRun.id.desc())
                .limit(limit)
            )
        )

    def get_for_portfolio(
        self, run_id: uuid.UUID, portfolio_id: uuid.UUID,
    ) -> OptimizationRun | None:
        return self._session.scalar(
            select(OptimizationRun).where(
                OptimizationRun.id == run_id,
                OptimizationRun.portfolio_id == portfolio_id,
            )
        )

    def delete(self, row: OptimizationRun) -> None:
        """Remove one run for its portfolio."""
        self._session.delete(row)
        self._session.flush()
