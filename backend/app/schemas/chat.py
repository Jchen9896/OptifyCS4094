"""HTTP schemas for the assistant chat API."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatSessionResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime


class ChatCitation(BaseModel):
    slug: str
    heading: str
    url: str


class PendingToolResponse(BaseModel):
    tool_call_id: uuid.UUID
    tool_name: str
    summary: str
    arguments: dict[str, Any]


class ChatMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    active_portfolio_id: uuid.UUID | None = None


class ChatMessageResponse(BaseModel):
    session_id: uuid.UUID
    reply: str
    citations: list[ChatCitation] = Field(default_factory=list)
    pending_tools: list[PendingToolResponse] = Field(default_factory=list)


class ChatConfirmRequest(BaseModel):
    tool_call_id: uuid.UUID
    accept: bool


class ChatConfirmResponse(BaseModel):
    session_id: uuid.UUID
    accepted: bool
    reply: str
    result: dict[str, Any] | None = None
