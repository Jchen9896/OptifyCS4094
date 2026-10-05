# Decision 001 — Frontend and backend

Use **React + TypeScript + Vite** for the frontend, **FastAPI** for the API, and **PostgreSQL** for storage.

## Local development

| Service | How it runs |
| --- | --- |
| PostgreSQL | Docker Compose + named volume |
| FastAPI | Docker Compose, connected to the `db` service |
| React + Vite | Host process (`npm run dev`) for faster hot reload |

Vite proxies `/api` to FastAPI. Add the frontend container (`docker compose --profile demo`) for demos or deployment-style runs.
