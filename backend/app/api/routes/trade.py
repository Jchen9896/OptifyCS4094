"""Trade order submission routes (Schwab)."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.current_user import get_current_user_id
from app.core.db import get_db
from app.schemas.trade import (
    SchwabAccountSummary,
    SubmitSchwabOrdersRequest,
    SubmitSchwabOrdersResponse,
)
from app.services.trade_service import TradeService, create_trade_service

router = APIRouter(prefix="/trade", tags=["trade"])


def get_trade_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TradeService:
    return create_trade_service(db, settings)


@router.get("/schwab/accounts", response_model=list[SchwabAccountSummary])
def list_schwab_trade_accounts(
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: TradeService = Depends(get_trade_service),
) -> list[SchwabAccountSummary]:
    return service.list_schwab_accounts(user_id)


@router.post("/schwab/orders", response_model=SubmitSchwabOrdersResponse)
def submit_schwab_orders(
    body: SubmitSchwabOrdersRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: TradeService = Depends(get_trade_service),
) -> SubmitSchwabOrdersResponse:
    return service.submit_schwab_orders(user_id, body)
