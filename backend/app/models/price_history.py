"""Daily price rows for the shared market-data table (database design v3 + Decision 006)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class PriceBarRow(Base):
    """One trading day's OHLCV for a symbol, with retrieval provenance.

    Named `PriceBarRow` so it does not clash with the provider `PriceBar` dataclass.
    """

    __tablename__ = "price_bars"
    __table_args__ = (
        CheckConstraint("open > 0", name="price_bars_open_positive"),
        CheckConstraint("high > 0", name="price_bars_high_positive"),
        CheckConstraint("low > 0", name="price_bars_low_positive"),
        CheckConstraint("close > 0", name="price_bars_close_positive"),
        CheckConstraint("volume >= 0", name="price_bars_volume_nonnegative"),
        CheckConstraint("high >= low", name="price_bars_high_gte_low"),
    )

    symbol: Mapped[str] = mapped_column(Text, ForeignKey("stocks.symbol"), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(Text, nullable=False)
    interval: Mapped[str] = mapped_column(Text, nullable=False)
    adjustment_basis: Mapped[str] = mapped_column(Text, nullable=False)
    calendar: Mapped[str] = mapped_column(Text, nullable=False)
