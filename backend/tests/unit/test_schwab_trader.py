import httpx
import pytest
from fastapi import HTTPException

from app.brokerage.schwab_trader import (
    equity_market_order_body,
    list_account_numbers,
    place_equity_market_order,
)


def test_equity_market_order_body_buy():
    body = equity_market_order_body(symbol="aapl", side="buy", quantity=3)
    assert body["orderType"] == "MARKET"
    assert body["orderLegCollection"][0]["instruction"] == "BUY"
    assert body["orderLegCollection"][0]["quantity"] == 3
    assert body["orderLegCollection"][0]["instrument"]["symbol"] == "AAPL"


def test_equity_market_order_rejects_fractional():
    with pytest.raises(HTTPException) as exc:
        equity_market_order_body(symbol="AAPL", side="buy", quantity=0)
    assert exc.value.status_code == 422


def test_list_account_numbers():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/accounts/accountNumbers")
        assert request.headers["Authorization"] == "Bearer access-1"
        return httpx.Response(
            200,
            json=[{"accountNumber": "1234", "hashValue": "hash-abc"}],
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    rows = list_account_numbers(access_token="access-1", client=client)
    assert rows == [{"account_number": "1234", "account_hash": "hash-abc"}]


def test_place_equity_market_order_reads_location():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/accounts/hash-abc/orders" in str(request.url)
        payload = request.read()
        assert b'"quantity":2' in payload
        assert b'"BUY"' in payload
        return httpx.Response(
            201,
            headers={
                "Location": "https://api.schwabapi.com/trader/v1/accounts/hash-abc/orders/998877"
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    order_id = place_equity_market_order(
        access_token="access-1",
        account_hash="hash-abc",
        symbol="MSFT",
        side="buy",
        quantity=2,
        client=client,
    )
    assert order_id == "998877"
