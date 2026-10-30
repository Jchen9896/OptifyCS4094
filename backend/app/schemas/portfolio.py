"""Portfolio request and response types."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AliasPath, BaseModel, ConfigDict, Field, field_validator, model_validator

Weight = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
PositiveNumber = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class PortfolioHoldingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=6, allow_inf_nan=False)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class PortfolioSetup(BaseModel):
    """Inputs used to restore the setup page, without a new price lookup."""

    model_config = ConfigDict(extra="forbid")

    initial_capital: PositiveNumber
    start_date: date
    end_date: date
    strategy: Literal["minvar", "mvo"]
    max_weight: float = Field(gt=0, le=1, allow_inf_nan=False)
    risk_free_rate: float = Field(allow_inf_nan=False)
    weights: dict[str, Weight]
    reference_prices: dict[str, PositiveNumber]

    @model_validator(mode="after")
    def check_dates(self) -> "PortfolioSetup":
        if self.start_date >= self.end_date:
            raise ValueError("The start date must be before the end date.")
        return self


class PortfolioCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    holdings: list[PortfolioHoldingInput] = Field(default_factory=list)
    setup: PortfolioSetup | None = None

    @model_validator(mode="after")
    def check_symbols(self) -> "PortfolioCreateRequest":
        symbols = [holding.symbol for holding in self.holdings]
        if len(symbols) != len(set(symbols)):
            raise ValueError("A portfolio cannot contain duplicate symbols.")
        if self.setup is not None:
            expected = set(symbols)
            if set(self.setup.weights) != expected or set(self.setup.reference_prices) != expected:
                raise ValueError("Setup weights and prices must match the holding symbols.")
        return self


class PortfolioUpdateRequest(BaseModel):
    """New portfolio name. The service rejects a blank name."""

    name: str


class PortfolioResponse(BaseModel):
    """Saved portfolio metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    created_at: datetime


class PortfolioHoldingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    name: str = Field(validation_alias=AliasPath("stock", "name"))
    quantity: Decimal


class PortfolioDetailResponse(PortfolioResponse):
    holdings: list[PortfolioHoldingResponse]
    setup: PortfolioSetup | None
