"""Allowlisted assistant tools. Writes are proposals until confirmed."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Callable

from google.genai import types
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import InvalidOptimizationInputError
from app.optimization.service import create_optimization_service
from app.schemas.optimization_run import OptimizationRunCreateRequest, OptimizationRunParams
from app.services.optimization_run_service import create_optimization_run_service
from app.services.portfolio_service import create_portfolio_service

READ_TOOLS = {
    "list_portfolios",
    "get_portfolio",
    "list_optimization_runs",
    "get_optimization_run",
}
WRITE_TOOLS = {
    "rename_portfolio",
    "delete_portfolio",
    "run_optimization",
}


def tool_declarations() -> list[types.FunctionDeclaration]:
    """Gemini function declarations for allowlisted tools."""
    return [
        types.FunctionDeclaration(
            name="list_portfolios",
            description="List the signed-in user's portfolios (id and name).",
            parameters=types.Schema(type=types.Type.OBJECT, properties={}),
        ),
        types.FunctionDeclaration(
            name="get_portfolio",
            description="Get one owned portfolio with holdings and setup fields.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "portfolio_id": types.Schema(type=types.Type.STRING),
                },
                required=["portfolio_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="list_optimization_runs",
            description="List recent optimization runs for an owned portfolio.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "portfolio_id": types.Schema(type=types.Type.STRING),
                    "limit": types.Schema(type=types.Type.INTEGER),
                },
                required=["portfolio_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="get_optimization_run",
            description="Get one owned optimization run detail.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "portfolio_id": types.Schema(type=types.Type.STRING),
                    "run_id": types.Schema(type=types.Type.STRING),
                },
                required=["portfolio_id", "run_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="rename_portfolio",
            description="Rename an owned portfolio. Requires UI confirmation.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "portfolio_id": types.Schema(type=types.Type.STRING),
                    "name": types.Schema(type=types.Type.STRING),
                },
                required=["portfolio_id", "name"],
            ),
        ),
        types.FunctionDeclaration(
            name="delete_portfolio",
            description="Delete an owned portfolio. Requires UI confirmation.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "portfolio_id": types.Schema(type=types.Type.STRING),
                },
                required=["portfolio_id"],
            ),
        ),
        types.FunctionDeclaration(
            name="run_optimization",
            description=(
                "Run optimization for an owned portfolio using its saved setup and "
                "persist the run. Requires UI confirmation. Not a trade."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "portfolio_id": types.Schema(type=types.Type.STRING),
                    "strategy": types.Schema(type=types.Type.STRING),
                    "start_date": types.Schema(type=types.Type.STRING),
                    "end_date": types.Schema(type=types.Type.STRING),
                    "max_weight": types.Schema(type=types.Type.NUMBER),
                    "risk_free_rate": types.Schema(type=types.Type.NUMBER),
                    "target_return": types.Schema(type=types.Type.NUMBER),
                    "target_volatility": types.Schema(type=types.Type.NUMBER),
                },
                required=["portfolio_id"],
            ),
        ),
    ]


def summarize_write_tool(name: str, arguments: dict[str, Any]) -> str:
    if name == "rename_portfolio":
        return f"Rename portfolio {arguments.get('portfolio_id')} to “{arguments.get('name')}”."
    if name == "delete_portfolio":
        return f"Delete portfolio {arguments.get('portfolio_id')}."
    if name == "run_optimization":
        return (
            f"Run {arguments.get('strategy') or 'saved'} optimization on portfolio "
            f"{arguments.get('portfolio_id')} and save the run."
        )
    return f"Run tool {name}."


class ToolExecutor:
    """Execute allowlisted tools for one user and DB session."""

    def __init__(self, session: Session, user_id: uuid.UUID) -> None:
        self._session = session
        self._user_id = user_id
        self._portfolios = create_portfolio_service(session)
        self._runs = create_optimization_run_service(session)

    def execute_read(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in READ_TOOLS:
            raise ValueError(f"Tool '{name}' is not a read tool.")
        return self._dispatch(name, arguments)

    def execute_write(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in WRITE_TOOLS:
            raise ValueError(f"Tool '{name}' is not a write tool.")
        return self._dispatch(name, arguments)

    def _dispatch(self, name: str, arguments: dict[str, Any]) -> Any:
        handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "list_portfolios": self._list_portfolios,
            "get_portfolio": self._get_portfolio,
            "list_optimization_runs": self._list_runs,
            "get_optimization_run": self._get_run,
            "rename_portfolio": self._rename_portfolio,
            "delete_portfolio": self._delete_portfolio,
            "run_optimization": self._run_optimization,
        }
        return handlers[name](arguments)

    def _list_portfolios(self, _arguments: dict[str, Any]) -> list[dict[str, str]]:
        rows = self._portfolios.list_portfolios(self._user_id)
        return [{"id": str(row.id), "name": row.name} for row in rows]

    def _get_portfolio(self, arguments: dict[str, Any]) -> dict[str, Any]:
        portfolio = self._portfolios.get_portfolio(uuid.UUID(arguments["portfolio_id"]), self._user_id)
        return {
            "id": str(portfolio.id),
            "name": portfolio.name,
            "setup": portfolio.setup,
            "holdings": [
                {"symbol": holding.symbol, "quantity": holding.quantity}
                for holding in portfolio.holdings
            ],
        }

    def _list_runs(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        limit = int(arguments.get("limit") or 20)
        rows = self._runs.list_runs(uuid.UUID(arguments["portfolio_id"]), self._user_id, limit=limit)
        return [row.model_dump(mode="json") for row in rows]

    def _get_run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        detail = self._runs.get_run(
            uuid.UUID(arguments["portfolio_id"]),
            uuid.UUID(arguments["run_id"]),
            self._user_id,
        )
        return detail.model_dump(mode="json")

    def _rename_portfolio(self, arguments: dict[str, Any]) -> dict[str, str]:
        portfolio = self._portfolios.update_portfolio(
            uuid.UUID(arguments["portfolio_id"]),
            self._user_id,
            str(arguments["name"]),
        )
        self._session.commit()
        return {"id": str(portfolio.id), "name": portfolio.name}

    def _delete_portfolio(self, arguments: dict[str, Any]) -> dict[str, str]:
        portfolio_id = uuid.UUID(arguments["portfolio_id"])
        self._portfolios.delete_portfolio(portfolio_id, self._user_id)
        self._session.commit()
        return {"deleted": str(portfolio_id)}

    def _run_optimization(self, arguments: dict[str, Any]) -> dict[str, Any]:
        portfolio_id = uuid.UUID(arguments["portfolio_id"])
        portfolio = self._portfolios.get_portfolio(portfolio_id, self._user_id)
        setup = portfolio.setup or {}
        holdings = setup.get("holdings") or []
        tickers = [str(item["symbol"]).upper() for item in holdings]
        if len(tickers) < 2:
            raise InvalidOptimizationInputError(
                "Portfolio needs at least two holdings in setup to optimize."
            )
        weights = [float(item.get("weightPercent", 0)) / 100.0 for item in holdings]
        weight_sum = sum(weights)
        current_weights = [value / weight_sum for value in weights] if weight_sum > 0 else None
        strategy = str(arguments.get("strategy") or setup.get("strategy") or "min_variance")
        start_raw = arguments.get("start_date") or setup.get("startDate")
        end_raw = arguments.get("end_date") or setup.get("endDate")
        if not start_raw or not end_raw:
            raise InvalidOptimizationInputError("Optimization needs start_date and end_date.")
        start_date = date.fromisoformat(str(start_raw))
        end_date = date.fromisoformat(str(end_raw))
        max_weight = arguments.get("max_weight")
        if max_weight is None and setup.get("maxWeightPercent") is not None:
            max_weight = float(setup["maxWeightPercent"]) / 100.0
        risk_free = arguments.get("risk_free_rate")
        if risk_free is None and setup.get("riskFreePercent") is not None:
            risk_free = float(setup["riskFreePercent"]) / 100.0
        target_return = arguments.get("target_return")
        if target_return is None and setup.get("targetReturnPercent") is not None:
            target_return = float(setup["targetReturnPercent"]) / 100.0
        target_volatility = arguments.get("target_volatility")
        if target_volatility is None and setup.get("targetVolatilityPercent") is not None:
            target_volatility = float(setup["targetVolatilityPercent"]) / 100.0
        initial_capital = setup.get("initialCapital")
        optimizer = create_optimization_service(get_settings(), self._session)
        result = optimizer.run(
            tickers,
            start_date,
            end_date,
            strategy=strategy,
            max_weight=float(max_weight) if max_weight is not None else None,
            risk_free_rate=float(risk_free) if risk_free is not None else None,
            current_weights=current_weights,
            initial_capital=float(initial_capital) if initial_capital else None,
            target_return=float(target_return) if target_return is not None else None,
            target_volatility=float(target_volatility) if target_volatility is not None else None,
        )
        params = OptimizationRunParams(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            strategy=strategy,
            max_weight=float(max_weight) if max_weight is not None else None,
            risk_free_rate=float(risk_free) if risk_free is not None else None,
            target_return=float(target_return) if target_return is not None else None,
            target_volatility=float(target_volatility) if target_volatility is not None else None,
            initial_capital=float(initial_capital) if initial_capital else None,
            current_weights=current_weights,
            reference_prices=setup.get("referencePrices"),
        )
        body = OptimizationRunCreateRequest(params=params, result=result)
        saved = self._runs.create_run(portfolio_id, self._user_id, body)
        self._session.commit()
        return {
            "run_id": str(saved.id),
            "strategy": saved.result.strategy,
            "expected_return": saved.result.expected_return,
            "volatility": saved.result.volatility,
            "sharpe_ratio": saved.result.sharpe_ratio,
        }
