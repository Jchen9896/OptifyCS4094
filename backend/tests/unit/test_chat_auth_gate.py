"""Chat routes require Gemini configuration."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.chat.service import create_chat_service
from app.core.config import Settings


def test_create_chat_service_requires_gemini_key():
    settings = Settings(gemini_api_key="")
    session = Session()
    try:
        create_chat_service(session, settings)
        assert False, "expected HTTPException"
    except HTTPException as error:
        assert error.status_code == 503
