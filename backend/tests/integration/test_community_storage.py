"""Community storage invariants on PostgreSQL."""

import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import get_settings


def test_community_reply_parent_cannot_cross_posts_and_post_delete_cascades():
    engine = create_engine(get_settings().database_url)
    with engine.begin() as connection:
        user_id = uuid.uuid4()
        post_a, post_b = uuid.uuid4(), uuid.uuid4()
        reply_id = uuid.uuid4()
        connection.execute(
            text("INSERT INTO users (id,email,oauth_provider,oauth_subject) VALUES (:id,:email,'clerk',:subject)"),
            {"id": user_id, "email": f"{user_id}@example.test", "subject": str(user_id)},
        )
        for post_id in (post_a, post_b):
            connection.execute(
                text("INSERT INTO community_posts (id,author_id,category,title,body) VALUES (:id,:author,'question','Title','Body')"),
                {"id": post_id, "author": user_id},
            )
        connection.execute(
            text("INSERT INTO community_replies (id,post_id,author_id,body) VALUES (:id,:post,:author,'parent')"),
            {"id": reply_id, "post": post_a, "author": user_id},
        )
        try:
            with connection.begin_nested():
                connection.execute(
                    text("INSERT INTO community_replies (post_id,parent_reply_id,author_id,body) VALUES (:post,:parent,:author,'invalid')"),
                    {"post": post_b, "parent": reply_id, "author": user_id},
                )
        except Exception as error:
            assert "community_replies_parent_same_post" in str(error)
        else:
            raise AssertionError("cross-post reply parent was accepted")
        connection.execute(text("DELETE FROM community_posts WHERE id=:id"), {"id": post_a})
        assert connection.scalar(text("SELECT count(*) FROM community_replies WHERE post_id=:id"), {"id": post_a}) == 0
    engine.dispose()
