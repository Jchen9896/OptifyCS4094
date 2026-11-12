"""Community categories, posts, and threaded replies."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.user import User


class CommunityCategory(Base):
    __tablename__ = "community_categories"

    slug: Mapped[str] = mapped_column(Text, primary_key=True)
    label: Mapped[str] = mapped_column(Text, nullable=False, unique=True)


class CommunityPost(Base):
    __tablename__ = "community_posts"
    __table_args__ = (
        Index("community_posts_page", "created_at", "id"),
        Index("community_posts_category_page", "category", "created_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    category: Mapped[str] = mapped_column(ForeignKey("community_categories.slug"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    author: Mapped[User | None] = relationship(foreign_keys=[author_id])


class CommunityReply(Base):
    __tablename__ = "community_replies"
    __table_args__ = (
        UniqueConstraint("post_id", "id", name="community_replies_post_id_id"),
        ForeignKeyConstraint(["post_id"], ["community_posts.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        ForeignKeyConstraint(
            ["post_id", "parent_reply_id"],
            ["community_replies.post_id", "community_replies.id"],
            ondelete="NO ACTION",
            name="community_replies_parent_same_post",
        ),
        CheckConstraint(
            "(deleted_at IS NULL AND body IS NOT NULL AND length(trim(body)) > 0) OR "
            "(deleted_at IS NOT NULL AND body IS NULL)",
            name="community_replies_live_or_tombstone",
        ),
        CheckConstraint("parent_reply_id IS NULL OR parent_reply_id <> id", name="community_replies_no_self_parent"),
        Index("community_replies_page", "post_id", "parent_reply_id", "created_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    parent_reply_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    author_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    body: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    author: Mapped[User | None] = relationship(foreign_keys=[author_id])
