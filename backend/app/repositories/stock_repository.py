"""Persist shared stock metadata (database design v3)."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.market_data.base import StockInfo
from app.models.stock import Stock


class StockRepository:
    """Insert or update one stock row. Session is injected for tests."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(self, stock: StockInfo) -> Stock:
        """Save `stock` by symbol. Update name, currency, and exchange when the row exists."""
        now = datetime.now(timezone.utc)
        row = self._session.get(Stock, stock.symbol)
        if row is None:
            row = Stock(
                symbol=stock.symbol,
                name=stock.name,
                currency=stock.currency,
                exchange=stock.exchange,
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.name = stock.name
            row.currency = stock.currency
            row.exchange = stock.exchange
            row.updated_at = now
        self._session.flush()
        return row
