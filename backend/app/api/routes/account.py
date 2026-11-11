"""Current-user account routes."""

import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.current_user import get_current_user_id
from app.core.db import get_db
from app.models.user import User

router = APIRouter(prefix="/account", tags=["account"])


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
