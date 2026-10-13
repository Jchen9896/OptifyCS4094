"""Expose historical calculations through an injected stored-price reader."""

from collections.abc import Sequence
from datetime import date

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.market_data.session_calendar import ExchangeSessionCalendar
from app.schemas.calculation import CalculationRequest, CalculationResponse
from app.services.stored_calculation_service import (
    PriceHistoryBatch, PriceHistoryReader, StoredCalculationService,
)

router = APIRouter(prefix="/calculations", tags=["calculations"])


class UnavailablePriceHistoryReader:
    """Fail clearly until the real price repository reader is connected."""

    def read_adjusted_history(
        self, tickers: Sequence[str], start_date: date, end_date: date
    ) -> PriceHistoryBatch:
        raise AppError(
            "Stored prices are unavailable. Try again later.",
            code="price_history_unavailable", status_code=503,
        )


def get_price_history_reader() -> PriceHistoryReader:
    """Replace this dependency with the repository reader when it is ready."""
    return UnavailablePriceHistoryReader()


def get_calculation_service(
    reader: PriceHistoryReader = Depends(get_price_history_reader),
    settings: Settings = Depends(get_settings),
) -> StoredCalculationService:
    return StoredCalculationService(
        reader, ExchangeSessionCalendar(settings.calculation_calendar),
        settings.calculation_annualization_factor,
    )


@router.post("", response_model=CalculationResponse)
def calculate(
    request: CalculationRequest,
    service: StoredCalculationService = Depends(get_calculation_service),
) -> CalculationResponse:
    result = service.calculate(
        request.tickers,
        request.start_date,
        request.end_date,
    )
    return CalculationResponse.from_result(result)
