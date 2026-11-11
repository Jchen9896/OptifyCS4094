"""Save optional setup inputs with each portfolio.

Revision ID: 20261029_0003
Revises: 20261028_0002
"""

import sqlalchemy as sa
from alembic import op

revision = "20261029_0003"
down_revision = "20261028_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("portfolios", sa.Column("setup", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("portfolios", "setup")
