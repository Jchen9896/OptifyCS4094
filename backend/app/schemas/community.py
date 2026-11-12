"""Community request and response models."""

import uuid
from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CommunityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PostCreate(CommunityRequest):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=10000)
    category: Literal["question", "discussion", "portfolio"]

    @field_validator("title", "body")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text cannot be blank.")
        return value.strip()


class PostUpdate(CommunityRequest):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    body: str | None = Field(default=None, min_length=1, max_length=10000)
    category: Literal["question", "discussion", "portfolio"] | None = None

    @field_validator("title", "body")
    @classmethod
    def require_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Text cannot be blank.")
        return value.strip() if value is not None else value


class ReplyCreate(CommunityRequest):
    body: str = Field(min_length=1, max_length=4000)
    parent_reply_id: uuid.UUID | None = None

    @field_validator("body")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text cannot be blank.")
        return value.strip()


class ReplyUpdate(CommunityRequest):
    body: str = Field(min_length=1, max_length=4000)

    @field_validator("body")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text cannot be blank.")
        return value.strip()


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None


class Author(BaseModel):
    name: str
    picture: str | None


class CategoryResponse(BaseModel):
    slug: str
    label: str


class PostResponse(BaseModel):
    id: uuid.UUID
    category: str
    title: str
    body: str
    created_at: datetime
    edited_at: datetime | None
    author: Author
    is_mine: bool


class ReplyResponse(BaseModel):
    id: uuid.UUID
    post_id: uuid.UUID
    parent_reply_id: uuid.UUID | None
    body: str | None
    created_at: datetime
    edited_at: datetime | None
    deleted_at: datetime | None
    author: Author | None
    is_mine: bool
