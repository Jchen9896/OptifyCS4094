# Decision 013 — RAG assistant (Gemini + confirmed tools)

## Decision

Add an authenticated **Assistant** that:

1. Retrieves Optify product knowledge from embedded Learn articles (and a short system-scope document) via **Gemini embeddings** stored in Postgres **pgvector**.
2. Loads **live** user portfolio and optimization-run data through allowlisted read tools (not a shared vector index).
3. May **propose** write tools (`rename_portfolio`, `delete_portfolio`, `run_optimization`) that execute only after explicit UI confirmation.
4. Never exposes trade, brokerage credential, or vault tools. Results stay historical estimates, not forecasts.

The LLM is **server-side Gemini** (`GEMINI_API_KEY` in `.env`). Defaults: chat `gemini-3.5-flash`, embeddings `gemini-embedding-001` (768-dim). User BYOK for chat is out of scope for v1.

## Why

Learn content already defines product scope and safe phrasing. User data must stay private and fresh, so it is fetched per request. Confirmed writes match the project rejection of unsupervised AI trading while still letting the assistant help with account actions.

## Consequences

- Compose Postgres image is `pgvector/pgvector:pg16`.
- Operators must run Alembic and `python -m app.chat.ingest` after deploy or article changes.
- Chat routes require a configured Gemini key; missing key returns 503.
