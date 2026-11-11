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


def _normalize_pem(value: str) -> str:
    """Accept Windows CRLF and escaped newlines from Compose env files."""
    return value.replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n").strip()


def _authorized_party_allowed(azp: object, settings: Settings) -> bool:
    """Allow missing azp, the app origins, or the Clerk issuer itself."""
    if not isinstance(azp, str) or not azp:
        return True
    party = azp.rstrip("/")
    allowed = {origin.rstrip("/") for origin in settings.cors_origin_list}
    allowed.add(settings.clerk_issuer.rstrip("/"))
    return party in allowed


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
            _normalize_pem(settings.clerk_jwt_key),
            algorithms=["RS256"],
            issuer=settings.clerk_issuer.rstrip("/"),
            options={"require": ["exp", "iat", "iss", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise unauthorized from exc
    if claims.get("sts") == "pending":
        raise unauthorized
    if not _authorized_party_allowed(claims.get("azp"), settings):
        raise unauthorized
    subject = claims.get("sub")
    email = claims.get("email")
    if not isinstance(subject, str) or not subject:
        raise unauthorized
    if not isinstance(email, str) or not email:
        raise HTTPException(status_code=401, detail="Clerk session is missing the email claim")
    return ClerkIdentity(subject=subject, email=email.strip().lower())
