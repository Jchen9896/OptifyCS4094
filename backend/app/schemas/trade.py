"""Trade / order submission schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SchwabAccountSummary(BaseModel):
    account_number: str
    account_hash: str


class TradeOrderLeg(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    side: Literal["buy", "sell"]
    quantity: int = Field(ge=1)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("symbol is required")
        return cleaned

    @field_validator("quantity")
    @classmethod
    def whole_shares_only(cls, value: int) -> int:
        if value != int(value) or value < 1:
            raise ValueError("quantity must be a whole number ≥ 1")
        return int(value)


class SubmitSchwabOrdersRequest(BaseModel):
    account_hash: str | None = None
    orders: list[TradeOrderLeg] = Field(min_length=1)


class SubmittedOrderResult(BaseModel):
    symbol: str
    side: Literal["buy", "sell"]
    quantity: int
    status: Literal["accepted", "rejected"]
    order_id: str | None = None
    message: str | None = None


class SubmitSchwabOrdersResponse(BaseModel):
    account_hash: str
    account_number: str | None = None
    results: list[SubmittedOrderResult]
