"""Community rules and response mapping."""

import uuid
from datetime import datetime, timezone

from app.core.current_user import CommunityPrincipal
from app.core.errors import AppError
from app.models.community import CommunityPost, CommunityReply
from app.models.user import User
from app.repositories.community_repository import CommunityRepository
from app.schemas.community import Author, CategoryResponse, Page, PostCreate, PostResponse, PostUpdate, ReplyCreate, ReplyResponse, ReplyUpdate
from app.services.community_cursor import decode_cursor, encode_cursor


class CommunityNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__("The Community item was not found.", code="community_not_found", status_code=404)


class CommunityService:
    def __init__(self, repository: CommunityRepository, page_size: int = 20, page_max: int = 50):
        self._repository = repository
        self._page_size = page_size
        self._page_max = page_max

    def categories(self) -> list[CategoryResponse]:
        return [CategoryResponse(slug=row.slug, label=row.label) for row in self._repository.categories()]

    def list_posts(self, category: str | None, cursor: str | None, limit: int | None, viewer: uuid.UUID) -> Page[PostResponse]:
        size = self._limit(limit)
        scope = f"posts:{category or '*'}"
        rows = self._repository.list_posts(category, decode_cursor(cursor, scope), size + 1)
        return self._post_page(rows, size, scope, viewer)

    def get_post(self, post_id: uuid.UUID, viewer: uuid.UUID) -> PostResponse:
        row = self._repository.post(post_id)
        if row is None:
            raise CommunityNotFoundError()
        return self._post(row, viewer)

    def create_post(self, principal: CommunityPrincipal, request: PostCreate) -> PostResponse:
        self._actor(principal)
        row = CommunityPost(author_id=principal.user_id, title=request.title.strip(), body=request.body.strip(), category=request.category)
        return self._post(self._repository.save(row), principal.user_id)

    def update_post(self, post_id: uuid.UUID, principal: CommunityPrincipal, request: PostUpdate) -> PostResponse:
        self._actor(principal)
        row = self._repository.locked_post(post_id, update=True)
        self._require_owner(row, principal.user_id)
        changes = request.model_dump(exclude_unset=True)
        if not changes:
            return self._post(row, principal.user_id)
        for field, value in changes.items():
            if value is not None:
                setattr(row, field, value.strip() if isinstance(value, str) else value)
        row.edited_at = datetime.now(timezone.utc)
        self._repository.flush()
        return self._post(row, principal.user_id)

    def delete_post(self, post_id: uuid.UUID, principal: CommunityPrincipal) -> None:
        self._actor(principal)
        row = self._repository.locked_post(post_id, update=True)
        self._require_owner(row, principal.user_id)
        self._repository.delete(row)

    def list_replies(self, post_id: uuid.UUID, parent_id: uuid.UUID | None, cursor: str | None, limit: int | None, viewer: uuid.UUID) -> Page[ReplyResponse]:
        if self._repository.post(post_id) is None:
            raise CommunityNotFoundError()
        if parent_id is not None and self._repository.reply(post_id, parent_id) is None:
            raise CommunityNotFoundError()
        scope = f"replies:{post_id}:{parent_id or '*'}"
        size = self._limit(limit)
        rows = self._repository.list_replies(post_id, parent_id, decode_cursor(cursor, scope), size + 1)
        has_more = len(rows) > size
        rows = rows[:size]
        next_cursor = encode_cursor(scope, rows[-1].created_at, rows[-1].id) if has_more else None
        return Page(items=[self._reply(row, viewer) for row in rows], next_cursor=next_cursor)

    def create_reply(self, post_id: uuid.UUID, principal: CommunityPrincipal, request: ReplyCreate) -> ReplyResponse:
        self._actor(principal)
        if self._repository.locked_post(post_id, update=False) is None:
            raise CommunityNotFoundError()
        if request.parent_reply_id is not None and self._repository.reply(post_id, request.parent_reply_id) is None:
            raise CommunityNotFoundError()
        row = CommunityReply(post_id=post_id, parent_reply_id=request.parent_reply_id, author_id=principal.user_id, body=request.body.strip())
        return self._reply(self._repository.save(row), principal.user_id)

    def update_reply(self, post_id: uuid.UUID, reply_id: uuid.UUID, principal: CommunityPrincipal, request: ReplyUpdate) -> ReplyResponse:
        self._actor(principal)
        if self._repository.locked_post(post_id, update=False) is None:
            raise CommunityNotFoundError()
        row = self._repository.reply(post_id, reply_id, update=True)
        self._require_owner(row, principal.user_id)
        if row.deleted_at is not None:
            raise CommunityNotFoundError()
        row.body = request.body.strip()
        row.edited_at = datetime.now(timezone.utc)
        self._repository.flush()
        return self._reply(row, principal.user_id)

    def delete_reply(self, post_id: uuid.UUID, reply_id: uuid.UUID, principal: CommunityPrincipal) -> None:
        self._actor(principal)
        if self._repository.locked_post(post_id, update=False) is None:
            raise CommunityNotFoundError()
        row = self._repository.reply(post_id, reply_id, update=True)
        self._require_owner(row, principal.user_id)
        if row.deleted_at is None:
            row.body = None
            row.deleted_at = datetime.now(timezone.utc)
            self._repository.flush()

    def _actor(self, principal: CommunityPrincipal) -> User:
        user = self._repository.lock_user(principal.user_id)
        if user is None:
            raise CommunityNotFoundError()
        user.public_name = principal.name
        user.avatar_url = principal.picture
        return user

    def _require_owner(self, row, user_id: uuid.UUID):
        if row is None or row.author_id != user_id:
            raise CommunityNotFoundError()
        return row

    def _limit(self, limit: int | None) -> int:
        limit = self._page_size if limit is None else limit
        if limit < 1 or limit > self._page_max:
            raise AppError(f"Page size must be between 1 and {self._page_max}.", code="invalid_page_size", status_code=422)
        return limit

    def _post_page(self, rows, size: int, scope: str, viewer: uuid.UUID) -> Page[PostResponse]:
        has_more = len(rows) > size
        rows = rows[:size]
        cursor = encode_cursor(scope, rows[-1].created_at, rows[-1].id) if has_more else None
        return Page(items=[self._post(row, viewer) for row in rows], next_cursor=cursor)

    def _post(self, row: CommunityPost, viewer: uuid.UUID) -> PostResponse:
        author = row.author
        return PostResponse(
            id=row.id, category=row.category, title=row.title, body=row.body,
            created_at=row.created_at, edited_at=row.edited_at,
            author=Author(name=author.public_name, picture=author.avatar_url) if author else Author(name="Member", picture=None),
            is_mine=row.author_id == viewer,
        )

    def _reply(self, row: CommunityReply, viewer: uuid.UUID | None = None) -> ReplyResponse:
        author = row.author
        return ReplyResponse(
            id=row.id, post_id=row.post_id, parent_reply_id=row.parent_reply_id, body=row.body,
            created_at=row.created_at, edited_at=row.edited_at, deleted_at=row.deleted_at,
            author=Author(name=author.public_name, picture=author.avatar_url) if author and row.deleted_at is None else None,
            is_mine=row.author_id is not None and row.author_id == viewer,
        )
