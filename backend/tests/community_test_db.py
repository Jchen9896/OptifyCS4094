import os

import pytest
from sqlalchemy import create_engine


ISOLATED_DATABASE_URL = "postgresql+psycopg2://community_test:community_test@127.0.0.1:37073/community_test"


def create_community_test_engine():
    if os.environ.get("DATABASE_URL") != ISOLATED_DATABASE_URL:
        pytest.skip("Community PostgreSQL tests require the exact isolated DATABASE_URL")
    return create_engine(ISOLATED_DATABASE_URL)
