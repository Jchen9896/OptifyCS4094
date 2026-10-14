"""Historical market data routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.schemas.market_data import PriceHistoryRequest, PriceHistoryResponse
from app.services.market_data_service import MarketDataService, create_market_data_service

router = APIRouter(prefix="/market-data", tags=["market-data"])


def get_market_data_service(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> MarketDataService:
    return create_market_data_service(settings, db)


@router.post("/history", response_model=PriceHistoryResponse)
def get_price_history(
    body: PriceHistoryRequest,
    service: MarketDataService = Depends(get_market_data_service),
) -> PriceHistoryResponse:
    """Return daily prices for one symbol. Prefer stored bars; fetch when needed."""
    result = service.get_or_fetch_history(body.symbol, body.start_date, body.end_date)
    return PriceHistoryResponse.model_validate(result)
