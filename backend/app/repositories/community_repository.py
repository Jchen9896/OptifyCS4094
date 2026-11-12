"""Database reads and flushes for Community records."""

import uuid
from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.community import CommunityCategory, CommunityPost, CommunityReply
from app.models.user import User


class CommunityRepository:
    def __init__(self, db: Session):
        self._db = db

    def categories(self) -> list[CommunityCategory]:
        return list(self._db.scalars(select(CommunityCategory).order_by(CommunityCategory.slug)))

    def list_posts(self, category: str | None, after: tuple[datetime, uuid.UUID] | None, limit: int):
        query = select(CommunityPost).where(CommunityPost.category == category) if category else select(CommunityPost)
        if after:
            query = query.where(
                or_(CommunityPost.created_at < after[0], and_(CommunityPost.created_at == after[0], CommunityPost.id < after[1]))
            )
        return list(self._db.scalars(query.options(selectinload(CommunityPost.author)).order_by(CommunityPost.created_at.desc(), CommunityPost.id.desc()).limit(limit)))

    def post(self, post_id: uuid.UUID) -> CommunityPost | None:
        return self._db.get(CommunityPost, post_id)

    def locked_post(self, post_id: uuid.UUID, *, update: bool) -> CommunityPost | None:
        return self._db.scalar(select(CommunityPost).where(CommunityPost.id == post_id).with_for_update(key_share=not update))

    def lock_user(self, user_id: uuid.UUID) -> User | None:
        return self._db.scalar(select(User).where(User.id == user_id).with_for_update())

    def list_replies(self, post_id: uuid.UUID, parent_id: uuid.UUID | None, after, limit: int):
        query = select(CommunityReply).where(
            CommunityReply.post_id == post_id,
            CommunityReply.parent_reply_id == parent_id,
        )
        if after:
            query = query.where(
                or_(CommunityReply.created_at > after[0], and_(CommunityReply.created_at == after[0], CommunityReply.id > after[1]))
            )
        return list(self._db.scalars(query.options(selectinload(CommunityReply.author)).order_by(CommunityReply.created_at, CommunityReply.id).limit(limit)))

    def reply(self, post_id: uuid.UUID, reply_id: uuid.UUID, *, update: bool = False) -> CommunityReply | None:
        query = select(CommunityReply).where(CommunityReply.post_id == post_id, CommunityReply.id == reply_id)
        return self._db.scalar(query.with_for_update() if update else query)

    def save(self, row):
        self._db.add(row)
        self._db.flush()
        return row

    def delete(self, row) -> None:
        self._db.delete(row)
        self._db.flush()

    def flush(self) -> None:
        self._db.flush()
