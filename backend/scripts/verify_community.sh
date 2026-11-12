#!/usr/bin/env bash
set -euo pipefail

expected='postgresql+psycopg2://community_test:community_test@127.0.0.1:37073/community_test'
if [[ "${DATABASE_URL:-}" != "$expected" ]]; then
    printf 'Set DATABASE_URL to the isolated Community verification database.\n' >&2
    exit 2
fi

cd "$(dirname "$0")/.."
export PYTHONPATH=.
python -m alembic downgrade 20261111_0006
python -m alembic upgrade head
python -m pytest -q
