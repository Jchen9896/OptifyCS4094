"""Clerk session verification stays independent of the database."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.auth import get_clerk_identity
from app.core.config import Settings


def test_clerk_session_verification():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    from cryptography.hazmat.primitives import serialization

    public_key = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    settings = Settings(clerk_issuer="https://example.clerk.accounts.dev", clerk_jwt_key=public_key)
    now = datetime.now(timezone.utc)
    claims = {
        "iss": settings.clerk_issuer, "sub": "user_123", "sid": "sess_123",
        "email": "Person@Example.com", "azp": "http://localhost:5173",
        "iat": now, "exp": now + timedelta(minutes=1),
    }

    def verify(changes, signing_key=key):
        token = jwt.encode({**claims, **changes}, signing_key, algorithm="RS256")
        return get_clerk_identity(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), settings)

    assert verify({}).subject == "user_123"
    assert verify({}).email == "person@example.com"
    without_origin = claims.copy()
    del without_origin["azp"]
    token = jwt.encode(without_origin, key, algorithm="RS256")
    assert get_clerk_identity(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), settings).subject == "user_123"
    assert verify({"azp": settings.clerk_issuer}).subject == "user_123"
    assert verify({"azp": "http://localhost:5173/"}).subject == "user_123"
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    for changes, signing_key in [
        ({"exp": now - timedelta(seconds=1)}, key),
        ({"iss": "https://other.example"}, key),
        ({"azp": "https://other.example"}, key),
        ({"sts": "pending"}, key),
        ({"email": ""}, key),
        ({}, other_key),
    ]:
        with pytest.raises(HTTPException) as error:
            verify(changes, signing_key)
        assert error.value.status_code == 401

    with pytest.raises(HTTPException) as error:
        get_clerk_identity(None, settings)
    assert error.value.status_code == 401


def test_clerk_jwt_key_accepts_windows_newlines():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    from cryptography.hazmat.primitives import serialization

    public_key = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode().replace("\n", "\r\n")
    settings = Settings(clerk_issuer="https://example.clerk.accounts.dev", clerk_jwt_key=public_key)
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "iss": settings.clerk_issuer,
            "sub": "user_123",
            "email": "person@example.com",
            "iat": now,
            "exp": now + timedelta(minutes=1),
        },
        key,
        algorithm="RS256",
    )

    identity = get_clerk_identity(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
        settings,
    )

    assert identity.subject == "user_123"
