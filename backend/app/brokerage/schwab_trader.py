"""Charles Schwab Trader API helpers (accounts + equity market orders)."""

from __future__ import annotations

import re
from typing import Any, Literal

import httpx
from fastapi import HTTPException

SCHWAB_TRADER_BASE = "https://api.schwabapi.com/trader/v1"
_LOCATION_ORDER_ID = re.compile(r"/orders/(\d+)")


def _auth_headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }


def list_account_numbers(
    *,
    access_token: str,
    client: httpx.Client | None = None,
) -> list[dict[str, str]]:
    """Return ``[{account_number, account_hash}, ...]`` from Schwab."""
    own_client = client is None
    http = client or httpx.Client(timeout=30.0)
    try:
        response = http.get(
            f"{SCHWAB_TRADER_BASE}/accounts/accountNumbers",
            headers=_auth_headers(access_token),
        )
    finally:
        if own_client:
            http.close()
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "schwab_accounts_failed",
                "message": f"Schwab account lookup failed ({response.status_code}).",
            },
        )
    payload = response.json()
    if not isinstance(payload, list):
        raise HTTPException(
            status_code=502,
            detail={"code": "schwab_accounts_invalid", "message": "Unexpected Schwab accounts payload."},
        )
    rows: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        number = item.get("accountNumber")
        hash_value = item.get("hashValue")
        if isinstance(number, str) and isinstance(hash_value, str) and number and hash_value:
            rows.append({"account_number": number, "account_hash": hash_value})
    return rows


def equity_market_order_body(
    *,
    symbol: str,
    side: Literal["buy", "sell"],
    quantity: int,
) -> dict[str, Any]:
    if quantity < 1:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_quantity", "message": "Order quantity must be a whole number ≥ 1."},
        )
    instruction = "BUY" if side == "buy" else "SELL"
    return {
        "orderType": "MARKET",
        "session": "NORMAL",
        "duration": "DAY",
        "orderStrategyType": "SINGLE",
        "orderLegCollection": [
            {
                "instruction": instruction,
                "quantity": quantity,
                "instrument": {"symbol": symbol.upper(), "assetType": "EQUITY"},
            }
        ],
    }


def place_equity_market_order(
    *,
    access_token: str,
    account_hash: str,
    symbol: str,
    side: Literal["buy", "sell"],
    quantity: int,
    client: httpx.Client | None = None,
) -> str | None:
    """Place a day market equity order. Returns Schwab order id when Location is present."""
    body = equity_market_order_body(symbol=symbol, side=side, quantity=quantity)
    own_client = client is None
    http = client or httpx.Client(timeout=30.0)
    try:
        response = http.post(
            f"{SCHWAB_TRADER_BASE}/accounts/{account_hash}/orders",
            headers={**_auth_headers(access_token), "Content-Type": "application/json"},
            json=body,
        )
    finally:
        if own_client:
            http.close()
    if response.status_code >= 400:
        message = f"Schwab rejected the order ({response.status_code})."
        try:
            payload = response.json()
            if isinstance(payload, dict):
                message = str(payload.get("message") or payload.get("detail") or message)
            elif isinstance(payload, list) and payload:
                first = payload[0]
                if isinstance(first, dict):
                    message = str(first.get("message") or first.get("detail") or message)
        except Exception:
            text = (response.text or "").strip()
            if text:
                message = text[:300]
        raise HTTPException(
            status_code=502,
            detail={"code": "schwab_order_rejected", "message": message, "symbol": symbol.upper()},
        )
    location = response.headers.get("location") or response.headers.get("Location") or ""
    match = _LOCATION_ORDER_ID.search(location)
    return match.group(1) if match else None
