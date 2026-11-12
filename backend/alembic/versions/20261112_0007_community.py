"""Add public profile fields and Community forum tables.

Revision ID: 20261112_0007
Revises: 20261111_0006
"""

import sqlalchemy as sa
from alembic import op

revision = "20261112_0007"
down_revision = "20261111_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("public_name", sa.Text(), server_default="Member", nullable=False))
    op.add_column("users", sa.Column("avatar_url", sa.Text(), nullable=True))
    op.create_table(
        "community_categories",
        sa.Column("slug", sa.Text(), primary_key=True),
        sa.Column("label", sa.Text(), nullable=False, unique=True),
    )
    op.create_table(
        "community_posts",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("author_id", sa.Uuid(), nullable=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["category"], ["community_categories.slug"]),
    )
    op.create_index("community_posts_page", "community_posts", ["created_at", "id"])
    op.create_index("community_posts_category_page", "community_posts", ["category", "created_at", "id"])
    op.create_table(
        "community_replies",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("parent_reply_id", sa.Uuid(), nullable=True),
        sa.Column("author_id", sa.Uuid(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("post_id", "id", name="community_replies_post_id_id"),
        sa.ForeignKeyConstraint(["post_id"], ["community_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["post_id", "parent_reply_id"], ["community_replies.post_id", "community_replies.id"],
            ondelete="NO ACTION", name="community_replies_parent_same_post",
        ),
        sa.CheckConstraint(
            "(deleted_at IS NULL AND body IS NOT NULL AND length(trim(body)) > 0) OR "
            "(deleted_at IS NOT NULL AND body IS NULL)",
            name="community_replies_live_or_tombstone",
        ),
        sa.CheckConstraint("parent_reply_id IS NULL OR parent_reply_id <> id", name="community_replies_no_self_parent"),
    )
    op.create_index("community_replies_page", "community_replies", ["post_id", "parent_reply_id", "created_at", "id"])
    op.bulk_insert(
        sa.table("community_categories", sa.column("slug"), sa.column("label")),
        [{"slug": slug, "label": label} for slug, label in (
            ("question", "Question"), ("discussion", "Discussion"), ("portfolio", "Portfolio")
        )],
    )


def downgrade() -> None:
    op.drop_index("community_replies_page", table_name="community_replies")
    op.drop_table("community_replies")
    op.drop_index("community_posts_category_page", table_name="community_posts")
    op.drop_index("community_posts_page", table_name="community_posts")
    op.drop_table("community_posts")
    op.drop_table("community_categories")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "public_name")
