# OptifyCS4094

Portfolio optimization for retail investors (CS 4094).

## For agents

Before writing or changing code, read the project steering docs in [`steering_docs/`](steering_docs/).

- **Coding style (required):** [`steering_docs/coding-style.md`](steering_docs/coding-style.md) — follow these conventions for all feature work unless a deviation is explicitly justified.
- Architecture: [`steering_docs/architecture.md`](steering_docs/architecture.md)
- API notes: [`steering_docs/api.md`](steering_docs/api.md)
- Decisions: [`steering_docs/decisions/`](steering_docs/decisions/)

Agents must not edit `steering_docs/coding-style.md` itself.

## Stack

| Service | Development setup | URL |
| --- | --- | --- |
| PostgreSQL | Docker Compose container + named volume | localhost:5432 |
| FastAPI | Docker Compose container, connected to PostgreSQL | http://localhost:8000 |
| React + Vite | Run locally with `npm run dev` | http://localhost:5173 |

Vite proxies `/api` to FastAPI. After Compose and Vite are running, http://localhost:5173 shows a setup page that reports whether the API and PostgreSQL are reachable.

## Prerequisites

- Node.js 18+
- Docker Desktop, running before Compose

A local Python venv is optional (tests / host-side scripts). Day-to-day API work uses the Compose `api` service.

## Run locally

**1. Copy environment variables** (from the repo root)

```bash
cp .env.example .env
```

On PowerShell: `Copy-Item .env.example .env`.

**2. Start PostgreSQL and FastAPI**

```bash
docker compose up -d --build
```

This starts `optify-db` and `optify-api`. Database files persist in the `optify_pgdata` volume.

- Health check: http://localhost:8000/api/health
- Docs: http://localhost:8000/docs

Compose mounts `backend/app` into the API container and runs uvicorn with `--reload`, so edits under `backend/app/` (routes, services, schemas, models) reload automatically. New route modules still need to be registered in `backend/app/api/router.py` with `include_router(...)`.

Rebuild the API image only when dependencies or the Dockerfile change:

```bash
docker compose up -d --build api
```

**3. Start the frontend** (from `frontend/`)

```bash
npm install
npm run dev
```

Open http://localhost:5173. The setup page should show **API reachable** and **Database reachable**.

### Optional: full-stack demo container

When you want the frontend in Compose too (demos / deployment-style run):

```bash
docker compose --profile demo up -d --build
```

Then open http://localhost:8080. Day-to-day UI work should still use Vite on the host for faster hot reload.

### Optional: host Python venv

You do **not** need a host venv to run the API. Compose builds the API image and installs Python dependencies inside the `optify-api` container.

Create a local venv only if you want to run pytest or host-side scripts (`scripts/check_db.py`) on your machine:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .
pytest
```

Confirm the DB from the repo root:

```bash
backend\.venv\Scripts\python scripts\check_db.py
```

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Database credentials | `optify` |
| `DATABASE_URL` | Host-side SQLAlchemy URL (`localhost`) | `postgresql+psycopg2://optify:optify@localhost:5432/optify` |
| `CORS_ORIGINS` | Allowed browser origins | `http://localhost:5173,http://127.0.0.1:5173` |
| `API_PORT` | Published FastAPI port | `8000` |
| `FRONTEND_PORT` | Published demo frontend port | `8080` |

Inside Compose, the API uses hostname `db` instead of `localhost`. Commit `.env.example` only. Keep `.env` local.

## Tests

Backend tests live in `backend/tests/` (`unit/`, `integration/`, `fixtures/`). Frontend tests live in `frontend/tests/`, grouped by feature.

Use the optional host venv above, then from `backend/`:

```bash
pytest
```

Test modules are placeholders until calculation, market data, and portfolio behavior is implemented.
