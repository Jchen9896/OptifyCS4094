"""Community endpoints use verified principals and transaction-backed storage."""

import uuid
from datetime import datetime, timezone

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.auth import ClerkIdentity, get_clerk_identity
from app.core.current_user import CommunityPrincipal, get_community_principal
from app.core.db import get_db
from app.main import create_app
from app.repositories.community_repository import CommunityRepository
from app.services.community_service import CommunityService
from app.api.routes.community import get_community_service


def test_every_community_route_requires_authentication():
    client = TestClient(create_app())
    requests = [
        ("get", "/api/community/categories", None),
        ("get", "/api/community/posts", None),
        ("post", "/api/community/posts", {"title": "x", "body": "x", "category": "question"}),
        ("get", f"/api/community/posts/{uuid.uuid4()}", None),
        ("patch", f"/api/community/posts/{uuid.uuid4()}", {"title": "x"}),
        ("delete", f"/api/community/posts/{uuid.uuid4()}", None),
        ("get", f"/api/community/posts/{uuid.uuid4()}/replies", None),
        ("post", f"/api/community/posts/{uuid.uuid4()}/replies", {"body": "x"}),
        ("patch", f"/api/community/posts/{uuid.uuid4()}/replies/{uuid.uuid4()}", {"body": "x"}),
        ("delete", f"/api/community/posts/{uuid.uuid4()}/replies/{uuid.uuid4()}", None),
    ]
    for method, path, body in requests:
        response = client.request(method.upper(), path, json=body)
        assert response.status_code == 401, (method, path, response.text)


def test_provisioning_rolls_back_on_write_or_commit_failure(community_test_engine):
    engine = community_test_engine

    def has_user(identity):
        with engine.connect() as connection:
            return connection.scalar(text("SELECT count(*) FROM users WHERE oauth_subject=:subject"), {"subject": identity.subject})

    success_identity = ClerkIdentity("community-first-user", "first-user@example.test", "New Member", None)
    success_app = create_app()
    success_app.dependency_overrides[get_clerk_identity] = lambda: success_identity
    created = TestClient(success_app).post(
        "/api/community/posts", json={"title": "First post", "body": "Body", "category": "question"}
    )
    assert created.status_code == 201 and has_user(success_identity) == 1
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM community_posts WHERE author_id=(SELECT id FROM users WHERE oauth_subject=:subject)"), {"subject": success_identity.subject})
        connection.execute(text("DELETE FROM users WHERE oauth_subject=:subject"), {"subject": success_identity.subject})

    failure_identity = ClerkIdentity("community-write-failure", "write-failure@example.test", "Failure", None)
    app = create_app()
    app.dependency_overrides[get_clerk_identity] = lambda: failure_identity

    class FailedWriteService:
        def create_post(self, _principal, _request):
            raise RuntimeError("forced write failure")

    app.dependency_overrides[get_community_service] = lambda: FailedWriteService()
    failed = TestClient(app, raise_server_exceptions=False).post(
        "/api/community/posts", json={"title": "Title", "body": "Body", "category": "question"}
    )
    assert failed.status_code == 500
    assert has_user(failure_identity) == 0

    commit_identity = ClerkIdentity("community-commit-failure", "commit-failure@example.test", "Failure", None)
    app = create_app()
    app.dependency_overrides[get_clerk_identity] = lambda: commit_identity

    class CommitFailureSession(Session):
        def commit(self):
            self.rollback()
            raise RuntimeError("forced commit failure")

    def fail_commit(db: Session = Depends(get_db, scope="function")):
        class FailureSessionService:
            def create_post(self, principal, request):
                return CommunityService(CommunityRepository(db)).create_post(principal, request)
        return FailureSessionService()

    def commit_failure_database():
        session = CommitFailureSession(bind=engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = commit_failure_database
    app.dependency_overrides[get_community_service] = fail_commit
    failed_commit = TestClient(app, raise_server_exceptions=False).post(
        "/api/community/posts", json={"title": "Title", "body": "Body", "category": "question"}
    )
    assert failed_commit.status_code == 500
    assert has_user(commit_identity) == 0


def test_post_reply_edit_delete_and_tombstone_response(community_test_engine):
    engine = community_test_engine
    owner_id, other_id = uuid.uuid4(), uuid.uuid4()
    with engine.begin() as connection:
        for user_id in (owner_id, other_id):
            connection.execute(
                text("INSERT INTO users (id,email,oauth_provider,oauth_subject) VALUES (:id,:email,'clerk',:subject)"),
                {"id": user_id, "email": f"{user_id}@example.test", "subject": str(user_id)},
            )
    app = create_app()
    picture = "https://images.clerk.dev/avatar.png"
    app.dependency_overrides[get_community_principal] = lambda: CommunityPrincipal(owner_id, "Taylor", picture)
    client = TestClient(app)
    post = client.post("/api/community/posts", json={"title": "Question", "body": "Body", "category": "question"})
    assert post.status_code == 201, post.text
    data = post.json()
    assert data["author"] == {"name": "Taylor", "picture": picture}
    assert "email" not in post.text and str(owner_id) not in post.text
    with engine.connect() as connection:
        profile = connection.execute(text("SELECT public_name, avatar_url FROM users WHERE id=:id"), {"id": owner_id}).one()
        assert profile == ("Taylor", picture)
    post_id = data["id"]
    second_post = client.post("/api/community/posts", json={"title": "Second", "body": "Body", "category": "question"})
    second_id = second_post.json()["id"]
    client.post("/api/community/posts", json={"title": "Third", "body": "Body", "category": "discussion"})
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE community_posts SET created_at=:stamp WHERE id IN (:first,:second)"),
            {"stamp": datetime(2099, 1, 1, tzinfo=timezone.utc), "first": post_id, "second": second_id},
        )
    first_page = client.get("/api/community/posts", params={"category": "question", "limit": 1})
    assert first_page.status_code == 200 and first_page.json()["next_cursor"]
    next_page = client.get("/api/community/posts", params={"category": "question", "limit": 1, "cursor": first_page.json()["next_cursor"]})
    assert next_page.status_code == 200
    assert [first_page.json()["items"][0]["id"], next_page.json()["items"][0]["id"]] == sorted([post_id, second_id], reverse=True)
    assert client.get("/api/community/posts", params={"category": "discussion", "cursor": first_page.json()["next_cursor"]}).status_code == 422
    assert client.get("/api/community/posts", params={"limit": 51}).status_code == 422
    reply = client.post(f"/api/community/posts/{post_id}/replies", json={"body": "Parent"})
    assert reply.status_code == 201, reply.text
    parent_id = reply.json()["id"]
    child = client.post(f"/api/community/posts/{post_id}/replies", json={"body": "Child", "parent_reply_id": parent_id})
    assert child.status_code == 201, child.text
    deep_parent = child.json()["id"]
    for depth in range(20):
        nested = client.post(f"/api/community/posts/{post_id}/replies", json={"body": f"Level {depth}", "parent_reply_id": deep_parent})
        assert nested.status_code == 201, nested.text
        deep_parent = nested.json()["id"]
    leaf = client.post(f"/api/community/posts/{post_id}/replies", json={"body": "Leaf", "parent_reply_id": deep_parent})
    assert leaf.status_code == 201
    leaf_page = client.get(f"/api/community/posts/{post_id}/replies", params={"parent_reply_id": deep_parent})
    assert [row["body"] for row in leaf_page.json()["items"]] == ["Leaf"]
    edited = client.patch(f"/api/community/posts/{post_id}", json={"title": "Changed"})
    assert edited.status_code == 200 and edited.json()["edited_at"]
    app.dependency_overrides[get_community_principal] = lambda: CommunityPrincipal(other_id, "Other", None)
    denied = client.patch(f"/api/community/posts/{post_id}", json={"title": "No"})
    assert denied.status_code == 404
    assert client.delete(f"/api/community/posts/{post_id}").status_code == 404
    assert client.patch(f"/api/community/posts/{post_id}/replies/{parent_id}", json={"body": "No"}).status_code == 404
    assert client.delete(f"/api/community/posts/{post_id}/replies/{parent_id}").status_code == 404
    app.dependency_overrides[get_community_principal] = lambda: CommunityPrincipal(owner_id, "Taylor", picture)
    reply_edit = client.patch(f"/api/community/posts/{post_id}/replies/{parent_id}", json={"body": "Edited parent"})
    assert reply_edit.status_code == 200 and reply_edit.json()["edited_at"]
    deleted = client.delete(f"/api/community/posts/{post_id}/replies/{parent_id}")
    assert deleted.status_code == 204
    assert client.delete(f"/api/community/posts/{post_id}/replies/{parent_id}").status_code == 204
    parent_page = client.get(f"/api/community/posts/{post_id}/replies")
    parent_json = parent_page.json()["items"][0]
    assert parent_json["body"] is None and parent_json["author"] is None
    descendants = client.get(f"/api/community/posts/{post_id}/replies", params={"parent_reply_id": parent_id})
    assert descendants.json()["items"][0]["body"] == "Child"
    assert client.patch(f"/api/community/posts/{post_id}/replies/{parent_id}", json={"body": "Restored"}).status_code == 404
    assert client.delete(f"/api/community/posts/{post_id}").status_code == 204
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM community_posts WHERE author_id=:owner"), {"owner": owner_id})
        connection.execute(text("DELETE FROM users WHERE id IN (:owner,:other)"), {"owner": owner_id, "other": other_id})
