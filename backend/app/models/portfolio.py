"""Portfolio row. One user owns many portfolios (database design v3)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Portfolio(Base):
    """A named portfolio for one user."""

    __tablename__ = "portfolios"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="portfolios_user_id_name"),
        Index("portfolios_user_id", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    holdings: Mapped[list["PortfolioHolding"]] = relationship(
        back_populates="portfolio",
        cascade="all, delete-orphan",
    )


# Register holdings so a portfolio delete also removes child rows.
from app.models import portfolio_position as _portfolio_position  # noqa: E402, F401
