"""Persist and read daily price bars (database design v3 + Decision 006)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.market_data.base import PriceBar
from app.models.price_history import PriceBarRow


class PriceRepository:
    """Upsert and range-read price bars. Session is injected for tests."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_bars(
        self,
        symbol: str,
        bars: list[PriceBar],
        *,
        fetched_at: datetime,
        source: str,
        interval: str,
        adjustment_basis: str,
        calendar: str,
    ) -> list[PriceBarRow]:
        """Save bars for `symbol` on `(symbol, date)`. Update OHLCV and provenance on conflict."""
        rows: list[PriceBarRow] = []
        for bar in bars:
            row = self._session.get(PriceBarRow, (symbol, bar.date))
            if row is None:
                row = PriceBarRow(
                    symbol=symbol,
                    date=bar.date,
                    open=Decimal(str(bar.open)),
                    high=Decimal(str(bar.high)),
                    low=Decimal(str(bar.low)),
                    close=Decimal(str(bar.close)),
                    volume=bar.volume,
                    fetched_at=fetched_at,
                    source=source,
                    interval=interval,
                    adjustment_basis=adjustment_basis,
                    calendar=calendar,
                )
                self._session.add(row)
            else:
                row.open = Decimal(str(bar.open))
                row.high = Decimal(str(bar.high))
                row.low = Decimal(str(bar.low))
                row.close = Decimal(str(bar.close))
                row.volume = bar.volume
                row.fetched_at = fetched_at
                row.source = source
                row.interval = interval
                row.adjustment_basis = adjustment_basis
                row.calendar = calendar
            rows.append(row)
        self._session.flush()
        return rows

    def list_range(self, symbol: str, start: date, end: date) -> list[PriceBarRow]:
        """Return stored bars for `symbol` from `start` to `end` inclusive, oldest first."""
        statement = (
            select(PriceBarRow)
            .where(
                PriceBarRow.symbol == symbol,
                PriceBarRow.date >= start,
                PriceBarRow.date <= end,
            )
            .order_by(PriceBarRow.date)
        )
        return list(self._session.scalars(statement).all())
