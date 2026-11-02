"""create users and portfolios

Revision ID: 20261028_0002
Revises: 20261014_0001
Create Date: 2026-10-28

Creates users, portfolios, and portfolio_holdings from database design v3.
Update and delete need these tables. Create and read routes are not in this change.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261028_0002"
down_revision: Union[str, Sequence[str], None] = "20261014_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("oauth_provider", sa.Text(), nullable=True),
        sa.Column("oauth_subject", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "password_hash IS NOT NULL OR (oauth_provider IS NOT NULL AND oauth_subject IS NOT NULL)",
            name="users_has_login_method",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="users_email_key"),
        sa.UniqueConstraint("oauth_provider", "oauth_subject", name="users_oauth_identity"),
    )
    op.create_table(
        "portfolios",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="portfolios_user_id_name"),
    )
    op.create_index("portfolios_user_id", "portfolios", ["user_id", "created_at"])
    op.create_table(
        "portfolio_holdings",
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("quantity > 0", name="portfolio_holdings_quantity_positive"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["symbol"], ["stocks.symbol"]),
        sa.PrimaryKeyConstraint("portfolio_id", "symbol"),
    )


def downgrade() -> None:
    op.drop_table("portfolio_holdings")
    op.drop_index("portfolios_user_id", table_name="portfolios")
    op.drop_table("portfolios")
    op.drop_table("users")
