"""Community cursors and request bodies reject invalid input."""

import base64
import json
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.community import PostCreate, ReplyCreate
from app.services.community_cursor import InvalidCommunityCursorError, decode_cursor, encode_cursor


def test_cursor_round_trip_and_scope_binding():
    stamp, row_id = datetime.now(timezone.utc), uuid.uuid4()
    cursor = encode_cursor("posts:question", stamp, row_id)
    assert decode_cursor(cursor, "posts:question") == (stamp, row_id)
    with pytest.raises(InvalidCommunityCursorError):
        decode_cursor(cursor, "posts:discussion")


@pytest.mark.parametrize("value", ["!", "not-base64", "a" * 1025])
def test_cursor_rejects_malformed_or_oversized_values(value):
    with pytest.raises(InvalidCommunityCursorError):
        decode_cursor(value, "posts:*")


def _encode_payload(payload):
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


@pytest.mark.parametrize(
    "payload",
    [
        {
            "version": 1,
            "scope": "posts:*",
            "stamp": "2026-01-01T00:00:00+00:00",
            "id": "00000000-0000-0000-0000-000000000000",
        },
        "not-a-cursor-list",
        [1, "posts:*", "2026-01-01T00:00:00+00:00"],
        [True, "posts:*", "2026-01-01T00:00:00+00:00", "00000000-0000-0000-0000-000000000000"],
        [1, [], "2026-01-01T00:00:00+00:00", "00000000-0000-0000-0000-000000000000"],
        [1, "posts:*", {}, "00000000-0000-0000-0000-000000000000"],
        [1, "posts:*", "2026-01-01T00:00:00+00:00", {}],
        [1, "posts:*", "2026-01-01T00:00:00+00:00", []],
        [1, "posts:*", "2026-01-01T00:00:00+00:00", None],
        [1, "posts:*", "2026-01-01T00:00:00", "00000000-0000-0000-0000-000000000000"],
        [1, "posts:*", "999999999999-01-01T00:00:00+00:00", "00000000-0000-0000-0000-000000000000"],
    ],
)
def test_cursor_rejects_invalid_decoded_payloads(payload):
    with pytest.raises(InvalidCommunityCursorError):
        decode_cursor(_encode_payload(payload), "posts:*")


def test_post_request_rejects_author_fields_and_blank_content():
    with pytest.raises(ValidationError):
        PostCreate(title="Title", body="Body", category="question", author_id=str(uuid.uuid4()))
    with pytest.raises(ValidationError):
        PostCreate(title="  ", body="Body", category="question")
    with pytest.raises(ValidationError):
        ReplyCreate(body="Reply", parent_reply_id=uuid.uuid4(), post_id=uuid.uuid4())
