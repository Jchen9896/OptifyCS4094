"""Request/response types for BYOK brokerage credentials (no secrets outbound)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

BrokerageProvider = Literal["schwab", "interactive_brokers", "alpaca", "etrade"]


class BrokerageCredentialUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_key: str = Field(min_length=1)
    app_secret: str = Field(min_length=1)
    # Optional; server overwrites with the canonical Schwab callback for schwab.
    callback_url: str | None = None

    @field_validator("app_key", "app_secret")
    @classmethod
    def strip_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be blank.")
        return cleaned

    @field_validator("callback_url")
    @classmethod
    def strip_optional_callback(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class BrokerageCredentialStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: BrokerageProvider
    callback_url: str
    app_key_hint: str
    updated_at: datetime
    authorized: bool = False


class SchwabOAuthSetup(BaseModel):
    callback_url: str
    frontend_redirect_url: str


class SchwabAuthorizeResponse(BaseModel):
    authorize_url: str
