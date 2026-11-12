import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.auth import ClerkIdentity
from app.core.db import Base
from app.core.current_user import get_community_principal, resolve_user
from app.models.user import User


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[User.__table__])
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_first_and_repeat_login_keep_same_local_id(db):
    identity = ClerkIdentity("user_123", "person@example.com")
    first = resolve_user(identity, db)
    assert isinstance(first, uuid.UUID)
    assert resolve_user(identity, db) == first
    assert db.query(User).count() == 1


def test_community_principal_resolves_user_and_signed_profile(db):
    principal = get_community_principal(ClerkIdentity("user_123", "person@example.com", "Taylor", None), db)
    user = db.get(User, principal.user_id)
    assert principal.name == "Taylor"
    assert principal.picture is None
    assert user.email == "person@example.com"
    assert user.public_name == "Member"


def test_existing_email_cannot_transfer_account(db):
    old_user = User(email="person@example.com", password_hash="legacy-hash")
    db.add(old_user)
    db.commit()
    with pytest.raises(HTTPException) as error:
        resolve_user(ClerkIdentity("user_123", "person@example.com"), db)
    assert error.value.status_code == 409
    assert db.query(User).count() == 1
