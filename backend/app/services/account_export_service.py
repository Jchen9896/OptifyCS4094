"""Build a downloadable Optify data export for the signed-in user."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.core.secret_box import decrypt_json
from app.models.brokerage_credential import BrokerageCredential
from app.models.community import CommunityPost, CommunityReply
from app.models.optimization_run import OptimizationRun
from app.models.portfolio import Portfolio
from app.models.portfolio_position import PortfolioHolding
from app.models.portfolio_risk_profile import PortfolioRiskProfile
from app.models.user import User


class AccountExportService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self._db = db
        self._settings = settings or get_settings()

    def build_export(self, user_id: uuid.UUID) -> dict[str, Any]:
        user = self._db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Account not found.")

        portfolios = list(
            self._db.scalars(
                select(Portfolio)
                .where(Portfolio.user_id == user_id)
                .options(selectinload(Portfolio.holdings).selectinload(PortfolioHolding.stock))
                .order_by(Portfolio.created_at.desc(), Portfolio.id.desc())
            )
        )
        portfolio_ids = [row.id for row in portfolios]
        runs_by_portfolio: dict[uuid.UUID, list[OptimizationRun]] = {pid: [] for pid in portfolio_ids}
        if portfolio_ids:
            runs = list(
                self._db.scalars(
                    select(OptimizationRun)
                    .where(OptimizationRun.portfolio_id.in_(portfolio_ids))
                    .order_by(OptimizationRun.created_at.desc(), OptimizationRun.id.desc())
                )
            )
            for run in runs:
                runs_by_portfolio.setdefault(run.portfolio_id, []).append(run)
        risk_profiles: dict[uuid.UUID, PortfolioRiskProfile] = {}
        if portfolio_ids:
            risk_profiles = {
                row.portfolio_id: row
                for row in self._db.scalars(
                    select(PortfolioRiskProfile).where(PortfolioRiskProfile.portfolio_id.in_(portfolio_ids))
                )
            }

        community_posts = list(
            self._db.scalars(
                select(CommunityPost).where(CommunityPost.author_id == user_id).order_by(CommunityPost.created_at, CommunityPost.id)
            )
        )
        community_replies = list(
            self._db.scalars(
                select(CommunityReply).where(CommunityReply.author_id == user_id).order_by(CommunityReply.created_at, CommunityReply.id)
            )
        )
        credentials = list(
            self._db.scalars(
                select(BrokerageCredential)
                .where(BrokerageCredential.user_id == user_id)
                .order_by(BrokerageCredential.provider.asc())
            )
        )

        return {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "format_version": 1,
            "user": {
                "id": str(user.id),
                "email": user.email,
            },
            "portfolios": [
                {
                    "id": str(portfolio.id),
                    "name": portfolio.name,
                    "created_at": portfolio.created_at.isoformat() if portfolio.created_at else None,
                    "setup": portfolio.setup,
                    "holdings": [
                        {
                            "symbol": holding.symbol,
                            "name": holding.stock.name if holding.stock is not None else holding.symbol,
                            "quantity": float(holding.quantity),
                            "added_at": holding.added_at.isoformat() if holding.added_at else None,
                        }
                        for holding in portfolio.holdings
                    ],
                    "optimization_runs": [
                        {
                            "id": str(run.id),
                            "created_at": run.created_at.isoformat() if run.created_at else None,
                            "params": run.params,
                            "result": run.result,
                        }
                        for run in runs_by_portfolio.get(portfolio.id, [])
                    ],
                    "risk_profile": self._risk_profile(risk_profiles.get(portfolio.id)),
                }
                for portfolio in portfolios
            ],
            "brokerage_connections": [self._brokerage_status(row) for row in credentials],
            "community_posts": [
                {
                    "id": str(row.id), "category": row.category, "title": row.title, "body": row.body,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "edited_at": row.edited_at.isoformat() if row.edited_at else None,
                }
                for row in community_posts
            ],
            "community_replies": [
                {
                    "id": str(row.id), "post_id": str(row.post_id),
                    "parent_reply_id": str(row.parent_reply_id) if row.parent_reply_id else None,
                    "body": row.body,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "edited_at": row.edited_at.isoformat() if row.edited_at else None,
                    "deleted_at": row.deleted_at.isoformat() if row.deleted_at else None,
                }
                for row in community_replies
            ],
        }

    def _risk_profile(self, row: PortfolioRiskProfile | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "questionnaire_version": row.questionnaire_version,
            "answers": row.answers,
            "capacity_score": row.capacity_score,
            "willingness_score": row.willingness_score,
            "score": row.score,
            "level": row.level,
            "recommendation": row.recommendation,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    def _brokerage_status(self, row: BrokerageCredential) -> dict[str, Any]:
        authorized = False
        try:
            secrets = decrypt_json(row.secrets_ciphertext, self._settings)
            authorized = bool(secrets.get("refresh_token"))
        except HTTPException:
            authorized = False
        return {
            "provider": row.provider,
            "callback_url": row.callback_url,
            "app_key_hint": row.app_key_hint,
            "authorized": authorized,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
