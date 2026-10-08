"""Stock response schemas."""

from pydantic import BaseModel, ConfigDict


class StockSearchResult(BaseModel):
    """One stock in the search results."""

    model_config = ConfigDict(from_attributes=True)

    symbol: str
    name: str
    exchange: str | None
    quote_type: str | None


class StockSearchResponse(BaseModel):
    """Search results. An empty `results` list means that no stock matches."""

    query: str
    results: list[StockSearchResult]
