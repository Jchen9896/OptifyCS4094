"""Read stored adjusted prices for calculation. Does not call the provider."""

from dataclasses import dataclass
from datetime import date

from app.core.errors import InsufficientHistoryError, InvalidPriceHistoryError
from app.market_data.base import PriceBar
from app.repositories.price_repository import PriceRepository


@dataclass(frozen=True)
class PriceHistoryBatch:
    """Adjusted daily prices grouped by ticker, with shared provenance."""

    histories: dict[str, list[PriceBar]]
    source: str
    interval: str
    adjustment_basis: str
    calendar: str


class StoredPriceHistoryReader:
    """Load price_bars through PriceRepository and check stored metadata."""

    def __init__(
        self,
        price_repository: PriceRepository,
        *,
        required_interval: str,
        required_adjustment_basis: str,
        required_calendar: str,
    ) -> None:
        self._price_repository = price_repository
        self._required_interval = required_interval
        self._required_adjustment_basis = required_adjustment_basis
        self._required_calendar = required_calendar

    def read_adjusted_history(
        self,
        tickers: list[str],
        start: date,
        end: date,
    ) -> PriceHistoryBatch:
        """Return stored prices for each ticker. Raise if history or metadata is unusable."""
        histories: dict[str, list[PriceBar]] = {}
        source = ""
        interval = ""
        adjustment_basis = ""
        calendar = ""

        for ticker in tickers:
            rows = self._price_repository.list_range(ticker, start, end)
            if not rows:
                raise InsufficientHistoryError(
                    f"No stored prices for {ticker} in the selected range. Load prices first."
                )
            for row in rows:
                if row.interval != self._required_interval:
                    raise InvalidPriceHistoryError(
                        f"Stored prices for {ticker} use interval '{row.interval}', "
                        f"but calculations require '{self._required_interval}'."
                    )
                if row.adjustment_basis != self._required_adjustment_basis:
                    raise InvalidPriceHistoryError(
                        f"Stored prices for {ticker} use basis '{row.adjustment_basis}', "
                        f"but calculations require '{self._required_adjustment_basis}'."
                    )
                if row.calendar != self._required_calendar:
                    raise InvalidPriceHistoryError(
                        f"Stored prices for {ticker} use calendar '{row.calendar}', "
                        f"but calculations require '{self._required_calendar}'."
                    )
            source = rows[0].source
            interval = rows[0].interval
            adjustment_basis = rows[0].adjustment_basis
            calendar = rows[0].calendar
            histories[ticker] = [
                PriceBar(
                    date=row.date,
                    open=float(row.open),
                    high=float(row.high),
                    low=float(row.low),
                    close=float(row.close),
                    volume=int(row.volume),
                )
                for row in rows
            ]

        return PriceHistoryBatch(
            histories=histories,
            source=source,
            interval=interval,
            adjustment_basis=adjustment_basis,
            calendar=calendar,
        )
