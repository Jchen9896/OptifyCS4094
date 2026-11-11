"""Assistant tool allowlist and write confirmation helpers."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.chat.service import ChatService
from app.chat.tools import READ_TOOLS, WRITE_TOOLS, summarize_write_tool
from app.core.config import Settings
from app.models.chat import ChatPendingTool, ChatSession


def test_read_and_write_tool_sets_are_disjoint():
    assert READ_TOOLS.isdisjoint(WRITE_TOOLS)
    assert "run_optimization" in WRITE_TOOLS
    assert "list_portfolios" in READ_TOOLS


def test_summarize_write_tool_names_actions():
    text = summarize_write_tool(
        "rename_portfolio",
        {"portfolio_id": "abc", "name": "Growth"},
    )
    assert "Growth" in text
    assert "abc" in text


def test_confirm_rejects_forged_pending_tool(monkeypatch):
    settings = Settings(gemini_api_key="test-key")
    session = Session()
    service = ChatService.__new__(ChatService)
    service._session = session
    service._settings = settings

    def fake_require(_session_id, _user_id):
        return ChatSession(id=uuid.uuid4(), user_id=uuid.uuid4())

    monkeypatch.setattr(service, "_require_session", fake_require)
    monkeypatch.setattr(
        session,
        "scalar",
        lambda *_args, **_kwargs: None,
    )

    with pytest.raises(HTTPException) as error:
        service.confirm_tool(uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), True)
    assert error.value.status_code == 404


def test_confirm_rejects_expired_pending_tool(monkeypatch):
    settings = Settings(gemini_api_key="test-key")
    session = Session()
    service = ChatService.__new__(ChatService)
    service._session = session
    service._settings = settings
    chat = ChatSession(id=uuid.uuid4(), user_id=uuid.uuid4())
    pending = ChatPendingTool(
        id=uuid.uuid4(),
        session_id=chat.id,
        user_id=chat.user_id,
        tool_name="delete_portfolio",
        arguments={"portfolio_id": str(uuid.uuid4())},
        summary="Delete portfolio",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    monkeypatch.setattr(service, "_require_session", lambda *_args, **_kwargs: chat)
    monkeypatch.setattr(session, "scalar", lambda *_args, **_kwargs: pending)
    deleted = []
    monkeypatch.setattr(session, "delete", lambda row: deleted.append(row))

    with pytest.raises(HTTPException) as error:
        service.confirm_tool(chat.id, chat.user_id, pending.id, True)
    assert error.value.status_code == 410
    assert deleted == [pending]
