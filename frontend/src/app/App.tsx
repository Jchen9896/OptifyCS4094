import { useEffect, useState } from 'react'
import { getHealth, type HealthResponse } from '../lib/apiClient.ts'

type LoadState =
  | { status: 'loading' }
  | { status: 'ok'; health: HealthResponse }
  | { status: 'error'; message: string }

export default function App() {
  const [state, setState] = useState<LoadState>({ status: 'loading' })

  useEffect(() => {
    getHealth()
      .then((health) => setState({ status: 'ok', health }))
      .catch((error: unknown) =>
        setState({
          status: 'error',
          message: error instanceof Error ? error.message : 'Health check failed.',
        }),
      )
  }, [])

  return (
    <main className="mx-auto flex min-h-svh max-w-xl flex-col justify-center gap-6 px-6">
      <div>
        <p className="text-sm tracking-wide text-mint uppercase">Optify</p>
        <h1 className="mt-1 text-3xl font-semibold text-paper">Local setup</h1>
        <p className="mt-2 text-muted">
          React, FastAPI, and PostgreSQL should all be reachable before feature work starts.
        </p>
      </div>

      <section className="rounded-xl border border-line bg-panel p-5">
        {state.status === 'loading' && <p className="text-muted">Checking /api/health…</p>}
        {state.status === 'ok' && (
          <ul className="space-y-2 text-sm">
            <StatusRow label="API" value={state.health.api} ok />
            <StatusRow label="Database" value={state.health.database} ok />
            <li className="flex justify-between gap-4 text-muted">
              <span>Checked</span>
              <span>{new Date(state.health.checked_at).toLocaleString()}</span>
            </li>
          </ul>
        )}
        {state.status === 'error' && (
          <div className="space-y-2">
            <StatusRow label="API / database" value="unreachable" ok={false} />
            <p className="text-sm text-danger">{state.message}</p>
            <p className="text-sm text-muted">
              Start Postgres with `docker compose up -d`, then the API with `uvicorn` from `backend/`.
            </p>
          </div>
        )}
      </section>
    </main>
  )
}

function StatusRow({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <li className="flex justify-between gap-4">
      <span className="text-muted">{label}</span>
      <span className={ok ? 'text-mint' : 'text-danger'}>{value}</span>
    </li>
  )
}
