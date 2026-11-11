"""Authenticated assistant chat routes."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.chat.service import ChatService, create_chat_service
from app.core.config import Settings, get_settings
from app.core.current_user import get_current_user_id
from app.core.db import get_db
from app.schemas.chat import (
    ChatConfirmRequest,
    ChatConfirmResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ChatService:
    return create_chat_service(db, settings)


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
def create_chat_session(
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: ChatService = Depends(get_chat_service),
) -> ChatSessionResponse:
    return service.create_session(user_id)


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
def post_chat_message(
    session_id: uuid.UUID,
    body: ChatMessageRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: ChatService = Depends(get_chat_service),
) -> ChatMessageResponse:
    return service.send_message(
        session_id,
        user_id,
        body.content.strip(),
        body.active_portfolio_id,
    )


@router.post("/sessions/{session_id}/confirm", response_model=ChatConfirmResponse)
def confirm_chat_tool(
    session_id: uuid.UUID,
    body: ChatConfirmRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: ChatService = Depends(get_chat_service),
) -> ChatConfirmResponse:
    return service.confirm_tool(session_id, user_id, body.tool_call_id, body.accept)
