"""Holding row. The table name is portfolio_holdings (database design v3)."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.portfolio import Portfolio
from app.models.stock import Stock


class PortfolioHolding(Base):
    """One symbol and share quantity inside a portfolio."""

    __tablename__ = "portfolio_holdings"
    __table_args__ = (CheckConstraint("quantity > 0", name="portfolio_holdings_quantity_positive"),)

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    symbol: Mapped[str] = mapped_column(Text, ForeignKey("stocks.symbol"), primary_key=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    portfolio: Mapped[Portfolio] = relationship(back_populates="holdings")
    stock: Mapped[Stock] = relationship()
