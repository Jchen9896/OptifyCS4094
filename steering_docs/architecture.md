# Architecture

Optify uses a layered layout:

- **Presentation:** React + Vite dashboard (`frontend/`), run on the host for hot reload
- **API:** FastAPI (`backend/app/`), run in Docker Compose for a shared team environment
- **Database:** PostgreSQL via Compose, with a named volume for persistence

Vite proxies `/api` to FastAPI on `localhost:8000`. A `frontend` Compose service exists under the `demo` profile when you want one-command full-stack startup.
