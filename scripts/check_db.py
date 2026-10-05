from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import text

from app.core.db import engine


def main() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    print("database reachable")


if __name__ == "__main__":
    main()
