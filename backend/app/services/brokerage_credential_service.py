"""Encrypt and manage per-user brokerage BYOK credentials."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.brokerage.oauth_state import create_oauth_state, verify_oauth_state
from app.brokerage.schwab_oauth import (
    build_authorize_url,
    exchange_authorization_code,
    refresh_access_token,
)
from app.core.config import Settings, get_settings
from app.core.secret_box import decrypt_json, encrypt_json
from app.repositories.brokerage_credential_repository import BrokerageCredentialRepository
from app.schemas.brokerage_credential import (
    BrokerageCredentialStatus,
    BrokerageCredentialUpsertRequest,
    BrokerageProvider,
    SchwabAuthorizeResponse,
    SchwabOAuthSetup,
)


def app_key_hint(app_key: str) -> str:
    cleaned = app_key.strip()
    return cleaned[-4:] if len(cleaned) >= 4 else cleaned


class BrokerageCredentialService:
    def __init__(
        self,
        repository: BrokerageCredentialRepository,
        settings: Settings | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings or get_settings()
        self._http_client = http_client

    def _status_for(self, row) -> BrokerageCredentialStatus:
        authorized = False
        try:
            secrets = decrypt_json(row.secrets_ciphertext, self._settings)
            authorized = bool(secrets.get("refresh_token"))
        except HTTPException:
            authorized = False
        return BrokerageCredentialStatus(
            provider=row.provider,
            callback_url=row.callback_url,
            app_key_hint=row.app_key_hint,
            updated_at=row.updated_at,
            authorized=authorized,
        )

    def list_status(self, user_id: uuid.UUID) -> list[BrokerageCredentialStatus]:
        return [self._status_for(row) for row in self._repository.list_for_user(user_id)]

    def schwab_setup(self) -> SchwabOAuthSetup:
        return SchwabOAuthSetup(
            callback_url=self._settings.schwab_oauth_callback_url,
            frontend_redirect_url=self._settings.settings_oauth_redirect_url,
        )

    def upsert(
        self,
        user_id: uuid.UUID,
        provider: BrokerageProvider,
        body: BrokerageCredentialUpsertRequest,
    ) -> BrokerageCredentialStatus:
        callback_url = (
            self._settings.schwab_oauth_callback_url
            if provider == "schwab"
            else (body.callback_url or "").strip()
        )
        if not callback_url:
            raise HTTPException(status_code=422, detail="callback_url is required for this provider.")
        if provider == "schwab" and not callback_url.startswith("https://"):
            raise HTTPException(
                status_code=422,
                detail="Schwab callback URL must use HTTPS. Set PUBLIC_API_BASE_URL accordingly.",
            )
        ciphertext = encrypt_json(
            {"app_key": body.app_key, "app_secret": body.app_secret},
            self._settings,
        )
        row = self._repository.upsert(
            user_id=user_id,
            provider=provider,
            callback_url=callback_url,
            app_key_hint=app_key_hint(body.app_key),
            secrets_ciphertext=ciphertext,
        )
        return self._status_for(row)

    def delete(self, user_id: uuid.UUID, provider: BrokerageProvider) -> None:
        row = self._repository.get_for_user(user_id, provider)
        if row is None:
            raise HTTPException(status_code=404, detail="Brokerage credentials not found.")
        self._repository.delete(row)

    def decrypt_secrets(self, user_id: uuid.UUID, provider: BrokerageProvider) -> dict[str, Any]:
        """Internal: decrypt vaulted secrets for OAuth (not an HTTP response)."""
        row = self._repository.get_for_user(user_id, provider)
        if row is None:
            raise HTTPException(status_code=404, detail="Brokerage credentials not found.")
        return decrypt_json(row.secrets_ciphertext, self._settings)

    def _write_secrets(self, user_id: uuid.UUID, provider: BrokerageProvider, secrets: dict[str, Any]):
        row = self._repository.get_for_user(user_id, provider)
        if row is None:
            raise HTTPException(status_code=404, detail="Brokerage credentials not found.")
        row.secrets_ciphertext = encrypt_json(secrets, self._settings)
        self._repository.upsert(
            user_id=user_id,
            provider=provider,
            callback_url=row.callback_url,
            app_key_hint=row.app_key_hint,
            secrets_ciphertext=row.secrets_ciphertext,
        )

    def start_schwab_authorize(self, user_id: uuid.UUID) -> SchwabAuthorizeResponse:
        secrets = self.decrypt_secrets(user_id, "schwab")
        app_key = secrets.get("app_key")
        if not isinstance(app_key, str) or not app_key:
            raise HTTPException(status_code=400, detail="Schwab App Key is missing from the vault.")
        callback_url = self._settings.schwab_oauth_callback_url
        state = create_oauth_state(user_id, self._settings)
        return SchwabAuthorizeResponse(
            authorize_url=build_authorize_url(
                app_key=app_key,
                callback_url=callback_url,
                state=state,
            )
        )

    def complete_schwab_callback(self, *, code: str, state: str) -> str:
        """Exchange code, store tokens, return frontend redirect URL."""
        user_id = verify_oauth_state(state, self._settings)
        row = self._repository.get_for_user(user_id, "schwab")
        if row is None:
            raise HTTPException(status_code=404, detail="Schwab credentials not found for this user.")
        secrets = decrypt_json(row.secrets_ciphertext, self._settings)
        app_key = secrets.get("app_key")
        app_secret = secrets.get("app_secret")
        if not isinstance(app_key, str) or not isinstance(app_secret, str):
            raise HTTPException(status_code=400, detail="Schwab App Key/Secret missing from the vault.")
        tokens = exchange_authorization_code(
            app_key=app_key,
            app_secret=app_secret,
            code=code,
            callback_url=self._settings.schwab_oauth_callback_url,
            client=self._http_client,
        )
        secrets.update(tokens)
        self._write_secrets(user_id, "schwab", secrets)
        query = urlencode({"schwab": "connected"})
        return f"{self._settings.settings_oauth_redirect_url}?{query}"

    def ensure_schwab_access_token(self, user_id: uuid.UUID) -> str:
        """Return a valid Schwab access token, refreshing when needed."""
        secrets = self.decrypt_secrets(user_id, "schwab")
        access = secrets.get("access_token")
        refresh = secrets.get("refresh_token")
        expires_raw = secrets.get("access_expires_at")
        app_key = secrets.get("app_key")
        app_secret = secrets.get("app_secret")
        if not isinstance(app_key, str) or not isinstance(app_secret, str):
            raise HTTPException(status_code=400, detail="Schwab App Key/Secret missing from the vault.")
        if not isinstance(refresh, str) or not refresh:
            raise HTTPException(
                status_code=401,
                detail={"code": "schwab_not_authorized", "message": "Authorize Schwab in Settings first."},
            )

        still_valid = False
        if isinstance(access, str) and access and isinstance(expires_raw, str):
            try:
                expires = datetime.fromisoformat(expires_raw)
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                still_valid = expires > datetime.now(timezone.utc)
            except ValueError:
                still_valid = False

        if still_valid and isinstance(access, str):
            return access

        tokens = refresh_access_token(
            app_key=app_key,
            app_secret=app_secret,
            refresh_token=refresh,
            client=self._http_client,
        )
        secrets.update(tokens)
        self._write_secrets(user_id, "schwab", secrets)
        return tokens["access_token"]


def create_brokerage_credential_service(
    db: Session,
    settings: Settings | None = None,
    http_client: httpx.Client | None = None,
) -> BrokerageCredentialService:
    return BrokerageCredentialService(BrokerageCredentialRepository(db), settings, http_client)
