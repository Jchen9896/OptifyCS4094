"""Delete account removes the local user and cascaded portfolios."""

import uuid

import pytest
from fastapi import Header
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.current_user import get_current_user_id
from app.core.db import Base, get_db
from app.main import create_app
from app.models.portfolio import Portfolio
from app.models.user import User


@pytest.fixture
def api():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        owner = User(email="owner@example.com", password_hash="test-only")
        session.add(owner)
        session.flush()
        session.add(Portfolio(user_id=owner.id, name="Core", holdings=[], setup=None))
        session.commit()
        user_id = owner.id

    def database():
        with Session(engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app = create_app()
    app.dependency_overrides[get_db] = database

    def current_user(authorization: str = Header(default="")):
        return user_id if authorization == "Bearer owner" else uuid.uuid4()

    app.dependency_overrides[get_current_user_id] = current_user
    with TestClient(app) as client:
        yield client, {"Authorization": "Bearer owner"}, engine, user_id
    engine.dispose()


def test_delete_account_removes_user_and_portfolios(api):
    client, owner, engine, user_id = api
    response = client.delete("/api/account", headers=owner)
    assert response.status_code == 204
    with Session(engine) as session:
        assert session.get(User, user_id) is None
        assert session.scalars(select(Portfolio)).all() == []
