"""Current-user account routes."""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.current_user import get_current_user_id
from app.core.db import get_db
from app.models.user import User
from app.services.account_export_service import AccountExportService

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/export")
def export_account_data(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Download this user's Optify data as JSON. Vault secrets are never included."""
    payload = AccountExportService(db, settings).build_export(user_id)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    body = json.dumps(payload, indent=2, default=str)
    return Response(
        content=body,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="optify-export-{stamp}.json"',
        },
    )


@router.delete("", status_code=204)
def delete_account(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Response:
    """Remove the local user row. Portfolios cascade with it."""
    account = db.get(User, user_id)
    if account is not None:
        db.delete(account)
        db.flush()
    return Response(status_code=204)
