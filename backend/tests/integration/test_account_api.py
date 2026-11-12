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
from app.models.community import CommunityCategory, CommunityPost, CommunityReply
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


def test_export_account_data_includes_portfolios(api):
    client, owner, _engine, user_id = api
    response = client.get("/api/account/export", headers=owner)
    assert response.status_code == 200
    assert "attachment" in response.headers.get("content-disposition", "")
    payload = response.json()
    assert payload["format_version"] == 1
    assert payload["user"]["id"] == str(user_id)
    assert len(payload["portfolios"]) == 1
    assert payload["portfolios"][0]["name"] == "Core"
    assert payload["brokerage_connections"] == []


def test_export_includes_only_own_community_content(api):
    client, owner, engine, user_id = api
    with Session(engine) as session:
        other = User(email="other@example.com", password_hash="test-only")
        session.add_all([other, CommunityCategory(slug="question", label="Question")])
        session.flush()
        other_id = other.id
        post = CommunityPost(author_id=user_id, category="question", title="Mine", body="My body")
        other_post = CommunityPost(author_id=other.id, category="question", title="Other", body="Private")
        session.add_all([post, other_post])
        session.flush()
        session.add(CommunityReply(post_id=post.id, author_id=user_id, body="My reply"))
        session.add(CommunityReply(post_id=other_post.id, author_id=other.id, body="Other reply"))
        session.commit()

    payload = client.get("/api/account/export", headers=owner).json()
    assert [row["title"] for row in payload["community_posts"]] == ["Mine"]
    assert [row["body"] for row in payload["community_replies"]] == ["My reply"]
    assert "Other" not in str(payload["community_posts"])
    assert str(other_id) not in str(payload)


def test_delete_account_removes_user_and_portfolios(api):
    client, owner, engine, user_id = api
    response = client.delete("/api/account", headers=owner)
    assert response.status_code == 204
    with Session(engine) as session:
        assert session.get(User, user_id) is None
        assert session.scalars(select(Portfolio)).all() == []
