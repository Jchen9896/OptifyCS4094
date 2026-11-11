"""Create optimization_runs for Compare history.

Revision ID: 20261111_0004
Revises: 20261029_0003
"""

import sqlalchemy as sa
from alembic import op

revision = "20261111_0004"
down_revision = "20261029_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "optimization_runs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "optimization_runs_portfolio_history",
        "optimization_runs",
        ["portfolio_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("optimization_runs_portfolio_history", table_name="optimization_runs")
    op.drop_table("optimization_runs")
