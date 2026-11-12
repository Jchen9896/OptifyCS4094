# Shared pytest fixtures for Optify backend tests.

import pytest
from sqlalchemy import text

from community_test_db import create_community_test_engine


@pytest.fixture
def community_test_engine():
    engine = create_community_test_engine()
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT current_database()")) == "community_test"
        yield engine
    finally:
        engine.dispose()
