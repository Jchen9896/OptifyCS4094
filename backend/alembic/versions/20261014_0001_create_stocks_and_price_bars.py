"""create stocks and price bars tables

Revision ID: 20261014_0001
Revises:
Create Date: 2026-10-14

Creates shared market-data tables from database design v3 plus Decision 006
provenance columns on price_bars.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261014_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stocks",
        sa.Column("symbol", sa.Text(), primary_key=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=True),
        sa.Column("exchange", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_table(
        "price_bars",
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(18, 4), nullable=False),
        sa.Column("high", sa.Numeric(18, 4), nullable=False),
        sa.Column("low", sa.Numeric(18, 4), nullable=False),
        sa.Column("close", sa.Numeric(18, 4), nullable=False),
        sa.Column("volume", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("interval", sa.Text(), nullable=False),
        sa.Column("adjustment_basis", sa.Text(), nullable=False),
        sa.Column("calendar", sa.Text(), nullable=False),
        sa.CheckConstraint("open > 0", name="price_bars_open_positive"),
        sa.CheckConstraint("high > 0", name="price_bars_high_positive"),
        sa.CheckConstraint("low > 0", name="price_bars_low_positive"),
        sa.CheckConstraint("close > 0", name="price_bars_close_positive"),
        sa.CheckConstraint("volume >= 0", name="price_bars_volume_nonnegative"),
        sa.CheckConstraint("high >= low", name="price_bars_high_gte_low"),
        sa.ForeignKeyConstraint(["symbol"], ["stocks.symbol"]),
        sa.PrimaryKeyConstraint("symbol", "date"),
    )


def downgrade() -> None:
    op.drop_table("price_bars")
    op.drop_table("stocks")
