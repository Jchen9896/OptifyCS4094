from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AppError

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise AppError(
            "The API is running but PostgreSQL is not reachable. "
            "Start the database with `docker compose up -d` and confirm DATABASE_URL.",
            code="database_unreachable",
            status_code=503,
        ) from exc

    return {
        "status": "ok",
        "api": "reachable",
        "database": "reachable",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
