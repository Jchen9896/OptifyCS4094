"""Map a verified Clerk account to the existing local user row."""

import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import ClerkIdentity, get_clerk_identity
from app.core.db import get_db
from app.models.user import User


def resolve_user(identity: ClerkIdentity, db: Session) -> uuid.UUID:
    account = db.scalar(select(User).where(User.oauth_provider == "clerk", User.oauth_subject == identity.subject))
    if account:
        return account.id
    if db.scalar(select(User.id).where(User.email == identity.email)):
        raise HTTPException(status_code=409, detail="Email already belongs to another account")
    try:
        with db.begin_nested():
            account = User(email=identity.email, oauth_provider="clerk", oauth_subject=identity.subject)
            db.add(account)
            db.flush()
        return account.id
    except IntegrityError:
        account = db.scalar(select(User).where(User.oauth_provider == "clerk", User.oauth_subject == identity.subject))
        if account:
            return account.id
        raise HTTPException(status_code=409, detail="Email already belongs to another account")


@dataclass(frozen=True)
class CommunityPrincipal:
    user_id: uuid.UUID
    name: str
    picture: str | None


def get_community_principal(
    identity: ClerkIdentity = Depends(get_clerk_identity),
    db: Session = Depends(get_db, scope="function"),
) -> CommunityPrincipal:
    return CommunityPrincipal(resolve_user(identity, db), identity.name, identity.picture)


def get_current_user_id(
    identity: ClerkIdentity = Depends(get_clerk_identity),
    db: Session = Depends(get_db),
) -> uuid.UUID:
    return resolve_user(identity, db)
