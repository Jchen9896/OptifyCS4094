"""Risk questionnaire and per-portfolio risk profile routes (Decision 014)."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.current_user import get_current_user_id
from app.core.db import get_db
from app.schemas.onboarding import QuestionnaireResponse, RiskProfileRequest, RiskProfileResponse
from app.services.risk_profile_service import RiskProfileService, create_risk_profile_service

router = APIRouter(tags=["onboarding"])


def get_risk_profile_service(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> RiskProfileService:
    return create_risk_profile_service(settings, db)


@router.get("/onboarding/questionnaire", response_model=QuestionnaireResponse)
def read_questionnaire(
    _user_id: uuid.UUID = Depends(get_current_user_id),
    service: RiskProfileService = Depends(get_risk_profile_service),
) -> QuestionnaireResponse:
    """Return the questions and answer options, without the points."""
    return service.get_questionnaire()


@router.put("/portfolios/{portfolio_id}/risk-profile", response_model=RiskProfileResponse)
def save_risk_profile(
    portfolio_id: uuid.UUID,
    body: RiskProfileRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: RiskProfileService = Depends(get_risk_profile_service),
) -> RiskProfileResponse:
    """Score the answers and save the profile. A new save replaces the old profile."""
    return service.save_profile(portfolio_id, user_id, body.answers)


@router.get("/portfolios/{portfolio_id}/risk-profile", response_model=RiskProfileResponse)
def read_risk_profile(
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    service: RiskProfileService = Depends(get_risk_profile_service),
) -> RiskProfileResponse:
    """Read the profile. A wrong owner gets the same 404 as a missing portfolio."""
    return service.get_profile(portfolio_id, user_id)
