"""Create portfolio_risk_profiles for onboarding (Decision 014).

Revision ID: 20261111_0007
Revises: 20261111_0006
"""

import sqlalchemy as sa
from alembic import op

revision = "20261111_0007"
down_revision = "20261111_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_risk_profiles",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("questionnaire_version", sa.Integer(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("capacity_score", sa.Float(), nullable=False),
        sa.Column("willingness_score", sa.Float(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("level", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("portfolio_id", name="portfolio_risk_profiles_portfolio_id"),
    )


def downgrade() -> None:
    op.drop_table("portfolio_risk_profiles")
