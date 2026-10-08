"""Stock search routes."""

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.stock import StockSearchResponse, StockSearchResult
from app.services.stock_service import StockService, create_stock_service

router = APIRouter(prefix="/stocks", tags=["stocks"])


def get_stock_service(settings: Settings = Depends(get_settings)) -> StockService:
    return create_stock_service(settings)


# `q` has an empty default, so the service gives the error for a missing query
# in the same format as all other application errors.
@router.get("", response_model=StockSearchResponse)
def search_stocks(q: str = "", service: StockService = Depends(get_stock_service)) -> StockSearchResponse:
    """Search for stocks by ticker or company name."""
    stocks = service.search_stocks(q)
    return StockSearchResponse(query=q, results=[StockSearchResult.model_validate(stock) for stock in stocks])
