"""BYOK brokerage credential vault + Schwab OAuth routes."""

import uuid

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.current_user import get_current_user_id
from app.core.db import get_db
from app.schemas.brokerage_credential import (
    BrokerageCredentialStatus,
    BrokerageCredentialUpsertRequest,
    BrokerageProvider,
    SchwabAuthorizeResponse,
    SchwabOAuthSetup,
)
from app.services.brokerage_credential_service import (
    BrokerageCredentialService,
    create_brokerage_credential_service,
)

router = APIRouter(prefix="/brokerage-credentials", tags=["brokerage-credentials"])


def get_brokerage_credential_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BrokerageCredentialService:
    return create_brokerage_credential_service(db, settings)


@router.get("", response_model=list[BrokerageCredentialStatus])
def list_brokerage_credentials(
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: BrokerageCredentialService = Depends(get_brokerage_credential_service),
) -> list[BrokerageCredentialStatus]:
    return service.list_status(user_id)


@router.get("/schwab/setup", response_model=SchwabOAuthSetup)
def schwab_oauth_setup(
    service: BrokerageCredentialService = Depends(get_brokerage_credential_service),
) -> SchwabOAuthSetup:
    """Public callback URL to register in the Schwab Developer Portal."""
    return service.schwab_setup()


@router.post("/schwab/authorize", response_model=SchwabAuthorizeResponse)
def start_schwab_authorize(
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: BrokerageCredentialService = Depends(get_brokerage_credential_service),
) -> SchwabAuthorizeResponse:
    """Build the Schwab LMS authorize URL (includes signed state)."""
    return service.start_schwab_authorize(user_id)


@router.get("/schwab/callback")
def schwab_oauth_callback(
    code: str = Query(min_length=1),
    state: str = Query(min_length=1),
    service: BrokerageCredentialService = Depends(get_brokerage_credential_service),
) -> RedirectResponse:
    """Schwab redirects here after consent. No Clerk JWT — auth is the signed state."""
    redirect_to = service.complete_schwab_callback(code=code, state=state)
    return RedirectResponse(url=redirect_to, status_code=302)


@router.put("/{provider}", response_model=BrokerageCredentialStatus)
def upsert_brokerage_credentials(
    provider: BrokerageProvider,
    body: BrokerageCredentialUpsertRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: BrokerageCredentialService = Depends(get_brokerage_credential_service),
) -> BrokerageCredentialStatus:
    return service.upsert(user_id, provider, body)


@router.delete("/{provider}", status_code=204)
def delete_brokerage_credentials(
    provider: BrokerageProvider,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: BrokerageCredentialService = Depends(get_brokerage_credential_service),
) -> Response:
    service.delete(user_id, provider)
    return Response(status_code=204)
