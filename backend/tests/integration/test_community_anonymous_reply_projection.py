import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.core.current_user import CommunityPrincipal, get_community_principal
from app.main import create_app


def test_live_reply_with_deleted_author_is_member_but_tombstone_is_anonymous():
    engine = create_engine(get_settings().database_url)
    author_id, viewer_id, post_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    private_email = f"community-test-{author_id}@example.test"
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT current_database()")) == "community_test"

    with engine.begin() as connection:
        for user_id in (author_id, viewer_id):
            connection.execute(
                text("INSERT INTO users (id,email,oauth_provider,oauth_subject) VALUES (:id,:email,'clerk',:subject)"),
                {
                    "id": user_id,
                    "email": private_email if user_id == author_id else f"community-test-{user_id}@example.test",
                    "subject": f"community-anonymous-test-{user_id}",
                },
            )

    app = create_app()
    app.dependency_overrides[get_community_principal] = lambda: CommunityPrincipal(author_id, "Reply Author", None)
    client = TestClient(app)
    try:
        post = client.post("/api/community/posts", json={"title": "Anonymous", "body": "Body", "category": "question"})
        assert post.status_code == 201, post.text
        post_id = uuid.UUID(post.json()["id"])

        live_reply = client.post(f"/api/community/posts/{post_id}/replies", json={"body": "Still visible"})
        tombstone = client.post(f"/api/community/posts/{post_id}/replies", json={"body": "Deleted later"})
        assert live_reply.status_code == 201, live_reply.text
        assert tombstone.status_code == 201, tombstone.text
        tombstone_id = tombstone.json()["id"]
        assert client.delete(f"/api/community/posts/{post_id}/replies/{tombstone_id}").status_code == 204

        with engine.begin() as connection:
            connection.execute(text("DELETE FROM users WHERE id=:id"), {"id": author_id})

        app.dependency_overrides[get_community_principal] = lambda: CommunityPrincipal(viewer_id, "Reader", None)
        response = client.get(f"/api/community/posts/{post_id}/replies")
        assert response.status_code == 200, response.text
        replies = {reply["body"]: reply for reply in response.json()["items"]}
        live_json = next(reply for reply in replies.values() if reply["body"] == "Still visible")
        tombstone_json = next(reply for reply in replies.values() if reply["body"] is None)

        assert live_json["author"] == {"name": "Member", "picture": None}
        assert live_json["is_mine"] is False
        assert tombstone_json["author"] is None
        assert tombstone_json["is_mine"] is False
        assert private_email not in response.text
        assert str(author_id) not in response.text
    finally:
        with engine.begin() as connection:
            if post_id:
                connection.execute(text("DELETE FROM community_posts WHERE id=:id"), {"id": post_id})
            connection.execute(text("DELETE FROM users WHERE id IN (:author,:viewer)"), {"author": author_id, "viewer": viewer_id})
        engine.dispose()
