"""Encode bounded, scoped Community keyset cursors."""

import base64
import binascii
import json
import uuid
from datetime import datetime

from app.core.errors import AppError


class InvalidCommunityCursorError(AppError):
    def __init__(self) -> None:
        super().__init__("The page cursor is invalid for this request.", code="invalid_cursor", status_code=422)


def encode_cursor(scope: str, created_at: datetime, row_id: uuid.UUID) -> str:
    payload = json.dumps([1, scope, created_at.isoformat(), str(row_id)], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def decode_cursor(value: str | None, scope: str) -> tuple[datetime, uuid.UUID] | None:
    if value is None:
        return None
    if len(value) > 1024:
        raise InvalidCommunityCursorError()
    try:
        raw = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
        version, cursor_scope, stamp, row_id = json.loads(raw)
        if version != 1 or cursor_scope != scope:
            raise ValueError
        return datetime.fromisoformat(stamp), uuid.UUID(row_id)
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError, binascii.Error):
        raise InvalidCommunityCursorError() from None
