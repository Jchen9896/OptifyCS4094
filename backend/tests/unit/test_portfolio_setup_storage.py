"""A setup snapshot survives a new database session; old rows stay valid."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.portfolio import Portfolio
from app.models.user import User


def test_setup_snapshot_round_trip_and_legacy_row():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    snapshot = {"initial_capital": 100000, "weights": {"AAPL": 100}}
    with Session(engine) as session:
        user = User(email="owner@example.com", password_hash="test-only")
        session.add(user)
        session.flush()
        saved = Portfolio(user_id=user.id, name="Saved", setup=snapshot)
        legacy = Portfolio(user_id=user.id, name="Legacy")
        session.add_all([saved, legacy])
        session.commit()
        saved_id, legacy_id = saved.id, legacy.id
    with Session(engine) as session:
        assert session.get(Portfolio, saved_id).setup == snapshot
        assert session.get(Portfolio, legacy_id).setup is None
    engine.dispose()
