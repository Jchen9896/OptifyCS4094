"""Verify Clerk sessions before using their account identity."""

from dataclasses import dataclass
from urllib.parse import urlsplit

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import COMMUNITY_AVATAR_URL_MAX, COMMUNITY_PROFILE_NAME_MAX, Settings, get_settings

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class ClerkIdentity:
    subject: str
    email: str
    name: str = "Member"
    picture: str | None = None


def _public_name(value: object) -> str:
    if not isinstance(value, str):
        return "Member"
    name = value.strip()
    if not name or len(name) > COMMUNITY_PROFILE_NAME_MAX or "@" in name or any(ord(char) < 32 for char in name):
        return "Member"
    return name


def _public_picture(value: object, settings: Settings) -> str | None:
    if not isinstance(value, str) or len(value) > COMMUNITY_AVATAR_URL_MAX:
        return None
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        allowed = {item.strip().lower() for item in settings.community_avatar_hosts.split(",") if item.strip()}
        if parsed.scheme != "https" or host not in allowed or parsed.username or parsed.password:
            return None
        if parsed.port not in (None, 443):
            return None
    except ValueError:
        return None
    return value


def _normalize_pem(value: str) -> str:
    """Accept Windows CRLF, escaped newlines, and quoted Compose env values."""
    normalized = value.replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n").strip()
    if (normalized.startswith("'") and normalized.endswith("'")) or (
        normalized.startswith('"') and normalized.endswith('"')
    ):
        normalized = normalized[1:-1].strip()
    return normalized


def _issuer_values(settings: Settings) -> list[str]:
    """Clerk may emit the issuer with or without a trailing slash."""
    base = settings.clerk_issuer.strip().rstrip("/")
    if not base:
        return []
    return [base, f"{base}/"]


def _authorized_party_allowed(azp: object, settings: Settings) -> bool:
    """Allow missing azp, the app origins, or the Clerk issuer itself."""
    if not isinstance(azp, str) or not azp:
        return True
    party = azp.rstrip("/")
    allowed = {origin.rstrip("/") for origin in settings.cors_origin_list}
    allowed.update(value.rstrip("/") for value in _issuer_values(settings))
    return party in allowed


def get_clerk_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> ClerkIdentity:
    issuers = _issuer_values(settings)
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing Authorization Bearer token")
    if not issuers or not settings.clerk_jwt_key:
        raise HTTPException(status_code=401, detail="Clerk issuer or JWT public key is not configured")
    try:
        # Clerk and the API host can disagree by a few seconds; without leeway, PyJWT
        # rejects tokens whose iat is slightly in the future ("not yet valid").
        claims = jwt.decode(
            credentials.credentials,
            _normalize_pem(settings.clerk_jwt_key),
            algorithms=["RS256"],
            issuer=issuers,
            leeway=60,
            options={"require": ["exp", "iat", "iss", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Clerk session token expired") from exc
    except jwt.InvalidIssuerError as exc:
        raise HTTPException(
            status_code=401,
            detail=f"Clerk token issuer mismatch (expected {issuers[0]})",
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid session ({exc})") from exc
    if claims.get("sts") == "pending":
        raise HTTPException(status_code=401, detail="Clerk session is still pending verification")
    azp = claims.get("azp")
    if not _authorized_party_allowed(azp, settings):
        allowed = sorted({origin.rstrip("/") for origin in settings.cors_origin_list})
        raise HTTPException(
            status_code=401,
            detail=(
                f"Clerk token azp '{azp}' is not allowed. "
                f"Add that origin to CORS_ORIGINS (currently {', '.join(allowed)})."
            ),
        )
    subject = claims.get("sub")
    email = claims.get("email")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(status_code=401, detail="Clerk session is missing the subject claim")
    if not isinstance(email, str) or not email:
        raise HTTPException(status_code=401, detail="Clerk session is missing the email claim")
    return ClerkIdentity(
        subject=subject,
        email=email.strip().lower(),
        name=_public_name(claims.get("name")),
        picture=_public_picture(claims.get("picture"), settings),
    )
