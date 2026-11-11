"""Orchestrate RAG retrieval, Gemini turns, and confirmed write tools."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from google.genai import types
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat.embeddings import EmbeddingClient
from app.chat.gemini_client import (
    GeminiChatClient,
    extract_function_calls,
    extract_text,
)
from app.chat.retriever import KnowledgeRetriever, RetrievedChunk
from app.chat.tools import READ_TOOLS, WRITE_TOOLS, ToolExecutor, summarize_write_tool
from app.core.config import Settings
from app.models.chat import ChatMessage, ChatPendingTool, ChatSession
from app.schemas.chat import (
    ChatCitation,
    ChatConfirmResponse,
    ChatMessageResponse,
    ChatSessionResponse,
    PendingToolResponse,
)
from app.services.portfolio_service import create_portfolio_service


class ChatService:
    """User-scoped assistant workflows."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        if not settings.gemini_api_key:
            raise HTTPException(status_code=503, detail="Gemini is not configured (GEMINI_API_KEY).")
        self._embedder = EmbeddingClient(settings)
        self._gemini = GeminiChatClient(settings)
        self._retriever = KnowledgeRetriever(
            session, self._embedder, top_k=settings.chat_rag_top_k
        )

    def create_session(self, user_id: uuid.UUID) -> ChatSessionResponse:
        row = ChatSession(user_id=user_id)
        self._session.add(row)
        self._session.flush()
        return ChatSessionResponse(id=row.id, created_at=row.created_at)

    def send_message(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
        active_portfolio_id: uuid.UUID | None,
    ) -> ChatMessageResponse:
        chat = self._require_session(session_id, user_id)
        retrieved = self._retriever.search(content)
        citations = [
            ChatCitation(**chunk.citation)
            for chunk in retrieved
            if chunk.source == "learn"
        ]
        # Deduplicate by slug+heading
        seen: set[tuple[str, str]] = set()
        unique_citations: list[ChatCitation] = []
        for item in citations:
            key = (item.slug, item.heading)
            if key in seen:
                continue
            seen.add(key)
            unique_citations.append(item)

        context = self._build_context(user_id, active_portfolio_id, retrieved)
        history = self._history_contents(chat)
        self._session.add(
            ChatMessage(session_id=chat.id, role="user", content=content, citations=None)
        )
        self._session.flush()

        response = self._gemini.generate(history=history, user_message=content, context_block=context)
        pending: list[PendingToolResponse] = []
        read_round = 0
        while read_round < 3:
            calls = extract_function_calls(response)
            if not calls:
                break
            read_calls = [(name, args) for name, args in calls if name in READ_TOOLS]
            write_calls = [(name, args) for name, args in calls if name in WRITE_TOOLS]
            unknown = [name for name, _ in calls if name not in READ_TOOLS and name not in WRITE_TOOLS]
            if unknown:
                raise HTTPException(status_code=400, detail=f"Unsupported tools: {', '.join(unknown)}")

            for name, args in write_calls:
                pending.append(self._queue_write(chat.id, user_id, name, args))

            if not read_calls:
                break

            executor = ToolExecutor(self._session, user_id)
            function_parts: list[types.Part] = []
            for name, args in read_calls:
                try:
                    result = executor.execute_read(name, args)
                    payload = json.dumps(result, default=str)
                except Exception as error:  # noqa: BLE001 - surface tool errors to the model
                    payload = json.dumps({"error": str(error)})
                function_parts.append(
                    types.Part.from_function_response(name=name, response={"result": payload})
                )
            response = self._gemini.continue_with_function_responses(
                history=history + [
                    types.Content(role="user", parts=[types.Part(text=context)]),
                    types.Content(
                        role="model",
                        parts=[
                            types.Part.from_function_call(name=name, args=args)
                            for name, args in read_calls
                        ],
                    ),
                ],
                function_response_parts=function_parts,
                context_block=context,
            )
            # Capture any additional write proposals from the follow-up turn.
            for name, args in extract_function_calls(response):
                if name in WRITE_TOOLS:
                    pending.append(self._queue_write(chat.id, user_id, name, args))
            read_round += 1

        reply = extract_text(response)
        if not reply and pending:
            reply = "I prepared an action that needs your confirmation below."
        if not reply:
            reply = "I could not produce a response. Try asking again with more detail."

        self._session.add(
            ChatMessage(
                session_id=chat.id,
                role="assistant",
                content=reply,
                citations=[item.model_dump() for item in unique_citations],
            )
        )
        self._session.flush()
        return ChatMessageResponse(
            session_id=chat.id,
            reply=reply,
            citations=unique_citations,
            pending_tools=pending,
        )

    def confirm_tool(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        tool_call_id: uuid.UUID,
        accept: bool,
    ) -> ChatConfirmResponse:
        chat = self._require_session(session_id, user_id)
        pending = self._session.scalar(
            select(ChatPendingTool).where(
                ChatPendingTool.id == tool_call_id,
                ChatPendingTool.session_id == chat.id,
                ChatPendingTool.user_id == user_id,
            )
        )
        if pending is None:
            raise HTTPException(status_code=404, detail="Pending tool call not found.")
        if pending.expires_at < datetime.now(timezone.utc):
            self._session.delete(pending)
            raise HTTPException(status_code=410, detail="Pending tool call expired.")

        if not accept:
            self._session.delete(pending)
            reply = f"Cancelled: {pending.summary}"
            self._session.add(ChatMessage(session_id=chat.id, role="assistant", content=reply))
            return ChatConfirmResponse(session_id=chat.id, accepted=False, reply=reply, result=None)

        if pending.tool_name not in WRITE_TOOLS:
            self._session.delete(pending)
            raise HTTPException(status_code=400, detail="Pending tool is not a writable allowlisted tool.")

        executor = ToolExecutor(self._session, user_id)
        result = executor.execute_write(pending.tool_name, pending.arguments)
        summary = pending.summary
        self._session.delete(pending)
        reply = f"Done: {summary}"
        self._session.add(ChatMessage(session_id=chat.id, role="assistant", content=reply))
        return ChatConfirmResponse(
            session_id=chat.id,
            accepted=True,
            reply=reply,
            result=result if isinstance(result, dict) else {"result": result},
        )

    def _queue_write(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str,
        arguments: dict,
    ) -> PendingToolResponse:
        summary = summarize_write_tool(name, arguments)
        row = ChatPendingTool(
            session_id=session_id,
            user_id=user_id,
            tool_name=name,
            arguments=arguments,
            summary=summary,
            expires_at=datetime.now(timezone.utc)
            + timedelta(seconds=self._settings.chat_pending_tool_ttl_seconds),
        )
        self._session.add(row)
        self._session.flush()
        return PendingToolResponse(
            tool_call_id=row.id,
            tool_name=name,
            summary=summary,
            arguments=arguments,
        )

    def _require_session(self, session_id: uuid.UUID, user_id: uuid.UUID) -> ChatSession:
        row = self._session.scalar(
            select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Chat session not found.")
        return row

    def _history_contents(self, chat: ChatSession) -> list[types.Content]:
        rows = self._session.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == chat.id)
            .order_by(ChatMessage.created_at)
            .limit(20)
        ).all()
        contents: list[types.Content] = []
        for row in rows:
            role = "user" if row.role == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=row.content)]))
        return contents

    def _build_context(
        self,
        user_id: uuid.UUID,
        active_portfolio_id: uuid.UUID | None,
        retrieved: list[RetrievedChunk],
    ) -> str:
        knowledge = "\n\n".join(
            f"[{chunk.slug} :: {chunk.heading}]\n{chunk.content}" for chunk in retrieved
        ) or "(no knowledge chunks retrieved)"
        portfolios = create_portfolio_service(self._session).list_portfolios(user_id)
        portfolio_lines = [f"- {row.name} ({row.id})" for row in portfolios] or ["- (none)"]
        active_line = "none"
        if active_portfolio_id is not None:
            match = next((row for row in portfolios if row.id == active_portfolio_id), None)
            if match is not None:
                active_line = f"{match.name} ({match.id})"
        return (
            "Retrieved knowledge:\n"
            f"{knowledge}\n\n"
            f"Active portfolio: {active_line}\n"
            "User portfolios:\n"
            + "\n".join(portfolio_lines)
        )


def create_chat_service(session: Session, settings: Settings) -> ChatService:
    return ChatService(session, settings)
