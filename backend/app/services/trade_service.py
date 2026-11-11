"""Submit reviewed trade legs to Schwab via the user's BYOK tokens."""

from __future__ import annotations

import uuid

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.brokerage.schwab_trader import list_account_numbers, place_equity_market_order
from app.core.config import Settings, get_settings
from app.schemas.trade import (
    SchwabAccountSummary,
    SubmitSchwabOrdersRequest,
    SubmitSchwabOrdersResponse,
    SubmittedOrderResult,
)
from app.services.brokerage_credential_service import BrokerageCredentialService


class TradeService:
    def __init__(
        self,
        credentials: BrokerageCredentialService,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._credentials = credentials
        self._http_client = http_client

    def list_schwab_accounts(self, user_id: uuid.UUID) -> list[SchwabAccountSummary]:
        token = self._credentials.ensure_schwab_access_token(user_id)
        rows = list_account_numbers(access_token=token, client=self._http_client)
        return [SchwabAccountSummary(**row) for row in rows]

    def submit_schwab_orders(
        self,
        user_id: uuid.UUID,
        body: SubmitSchwabOrdersRequest,
    ) -> SubmitSchwabOrdersResponse:
        accounts = self.list_schwab_accounts(user_id)
        if not accounts:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "schwab_no_accounts",
                    "message": "No Schwab brokerage accounts were returned for this authorization.",
                },
            )

        selected = None
        if body.account_hash:
            selected = next((row for row in accounts if row.account_hash == body.account_hash), None)
            if selected is None:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "schwab_account_unknown",
                        "message": "The selected Schwab account hash is not available for this user.",
                    },
                )
        else:
            selected = accounts[0]

        # Fresh token in case listing already refreshed once.
        access_token = self._credentials.ensure_schwab_access_token(user_id)
        results: list[SubmittedOrderResult] = []
        for leg in body.orders:
            try:
                order_id = place_equity_market_order(
                    access_token=access_token,
                    account_hash=selected.account_hash,
                    symbol=leg.symbol,
                    side=leg.side,
                    quantity=leg.quantity,
                    client=self._http_client,
                )
                results.append(
                    SubmittedOrderResult(
                        symbol=leg.symbol,
                        side=leg.side,
                        quantity=leg.quantity,
                        status="accepted",
                        order_id=order_id,
                        message=None,
                    )
                )
            except HTTPException as exc:
                detail = exc.detail
                message = "Order rejected by Schwab."
                if isinstance(detail, dict):
                    message = str(detail.get("message") or message)
                elif isinstance(detail, str):
                    message = detail
                results.append(
                    SubmittedOrderResult(
                        symbol=leg.symbol,
                        side=leg.side,
                        quantity=leg.quantity,
                        status="rejected",
                        order_id=None,
                        message=message,
                    )
                )

        return SubmitSchwabOrdersResponse(
            account_hash=selected.account_hash,
            account_number=selected.account_number,
            results=results,
        )


def create_trade_service(
    db: Session,
    settings: Settings | None = None,
    http_client: httpx.Client | None = None,
) -> TradeService:
    from app.services.brokerage_credential_service import create_brokerage_credential_service

    credentials = create_brokerage_credential_service(db, settings or get_settings(), http_client)
    return TradeService(credentials, http_client)
