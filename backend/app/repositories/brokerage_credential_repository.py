"""Persist encrypted brokerage credentials through an injected session."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.brokerage_credential import BrokerageCredential


class BrokerageCredentialRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_user(self, user_id: uuid.UUID) -> list[BrokerageCredential]:
        return list(
            self._session.scalars(
                select(BrokerageCredential)
                .where(BrokerageCredential.user_id == user_id)
                .order_by(BrokerageCredential.provider.asc())
            )
        )

    def get_for_user(self, user_id: uuid.UUID, provider: str) -> BrokerageCredential | None:
        return self._session.scalar(
            select(BrokerageCredential).where(
                BrokerageCredential.user_id == user_id,
                BrokerageCredential.provider == provider,
            )
        )

    def upsert(
        self,
        *,
        user_id: uuid.UUID,
        provider: str,
        callback_url: str,
        app_key_hint: str,
        secrets_ciphertext: str,
    ) -> BrokerageCredential:
        row = self.get_for_user(user_id, provider)
        if row is None:
            row = BrokerageCredential(
                user_id=user_id,
                provider=provider,
                callback_url=callback_url,
                app_key_hint=app_key_hint,
                secrets_ciphertext=secrets_ciphertext,
            )
            self._session.add(row)
        else:
            row.callback_url = callback_url
            row.app_key_hint = app_key_hint
            row.secrets_ciphertext = secrets_ciphertext
        self._session.flush()
        return row

    def delete(self, row: BrokerageCredential) -> None:
        self._session.delete(row)
        self._session.flush()
