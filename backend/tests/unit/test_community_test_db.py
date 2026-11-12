import pytest

import community_test_db


@pytest.mark.parametrize("database_url", [None, "postgresql://other/database"])
def test_unisolated_community_database_skips_before_engine_creation(monkeypatch, database_url):
    if database_url is None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("DATABASE_URL", database_url)

    def unexpected_engine_creation(_url):
        raise AssertionError("create_engine must not run for an unisolated database URL")

    monkeypatch.setattr(community_test_db, "create_engine", unexpected_engine_creation)

    with pytest.raises(pytest.skip.Exception, match="exact isolated DATABASE_URL"):
        community_test_db.create_community_test_engine()
