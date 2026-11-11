"""Create brokerage_credentials for BYOK secrets vault.

Revision ID: 20261111_0005
Revises: 20261111_0004
"""

import sqlalchemy as sa
from alembic import op

revision = "20261111_0005"
down_revision = "20261111_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brokerage_credentials",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("callback_url", sa.Text(), nullable=False),
        sa.Column("app_key_hint", sa.Text(), nullable=False),
        sa.Column("secrets_ciphertext", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "provider", name="brokerage_credentials_user_provider"),
    )


def downgrade() -> None:
    op.drop_table("brokerage_credentials")
