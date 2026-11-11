"""Verify Clerk sessions before using their account identity."""

from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class ClerkIdentity:
    subject: str
    email: str


def get_clerk_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> ClerkIdentity:
    unauthorized = HTTPException(status_code=401, detail="Invalid session")
    if not credentials or not settings.clerk_issuer or not settings.clerk_jwt_key:
        raise unauthorized
    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.clerk_jwt_key.replace("\\n", "\n"),
            algorithms=["RS256"],
            issuer=settings.clerk_issuer,
            options={"require": ["exp", "iat", "iss", "sub", "sid", "azp"]},
        )
    except jwt.PyJWTError as exc:
        raise unauthorized from exc
    if claims.get("azp") not in settings.cors_origin_list or claims.get("sts") == "pending":
        raise unauthorized
    subject = claims.get("sub")
    email = claims.get("email")
    if not isinstance(subject, str) or not subject or not isinstance(email, str) or not email:
        raise unauthorized
    return ClerkIdentity(subject=subject, email=email.strip().lower())
