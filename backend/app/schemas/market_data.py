"""Request and response schemas for historical market data."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PriceHistoryRequest(BaseModel):
    """One symbol and an inclusive history window."""

    symbol: str = Field(min_length=1)
    start_date: date
    end_date: date


class PriceHistoryResponse(BaseModel):
    """Stored history summary for the requested window."""

    model_config = ConfigDict(from_attributes=True)

    symbol: str
    start_date: date
    end_date: date
    bar_count: int
    first_date: date | None
    last_date: date | None
    source: str
    fetched_at: datetime | None
    served_from_database: bool
