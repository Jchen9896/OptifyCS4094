"""Unit tests for request-scoped database session commit behavior."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.db import get_db


def test_get_db_commits_on_success():
    session = MagicMock()
    with patch("app.core.db.SessionLocal", return_value=session):
        generator = get_db()
        assert next(generator) is session
        with pytest.raises(StopIteration):
            next(generator)

    session.commit.assert_called_once()
    session.rollback.assert_not_called()
    session.close.assert_called_once()


def test_get_db_rolls_back_on_error():
    session = MagicMock()
    with patch("app.core.db.SessionLocal", return_value=session):
        generator = get_db()
        next(generator)
        with pytest.raises(RuntimeError, match="boom"):
            generator.throw(RuntimeError("boom"))

    session.rollback.assert_called_once()
    session.commit.assert_not_called()
    session.close.assert_called_once()
