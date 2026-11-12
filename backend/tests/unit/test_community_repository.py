import uuid

from sqlalchemy.dialects import postgresql

from app.repositories.community_repository import CommunityRepository


class RecordingSession:
    def scalar(self, statement):
        self.statement = statement
        return None


def test_locked_post_read_uses_key_share_lock():
    session = RecordingSession()

    CommunityRepository(session).locked_post(uuid.uuid4(), update=False)

    sql = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "FOR KEY SHARE" in sql
    assert "FOR NO KEY UPDATE" not in sql


def test_locked_post_update_uses_update_lock():
    session = RecordingSession()

    CommunityRepository(session).locked_post(uuid.uuid4(), update=True)

    sql = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in sql
    assert "FOR KEY SHARE" not in sql
