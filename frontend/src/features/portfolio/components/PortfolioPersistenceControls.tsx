import { useState } from 'react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ApiError } from '@/lib/apiClient'
import {
  createPortfolio, listPortfolios, readPortfolio, restorePortfolio,
  type PortfolioDraft, type PortfolioSummary,
} from '../portfolioApi.ts'

type Props = {
  draft: PortfolioDraft
  onLoad: (draft: PortfolioDraft) => void
  onNew: () => void
  disabled: boolean
}

export default function PortfolioPersistenceControls({ draft, onLoad, onNew, disabled }: Props) {
  const [userId, setUserId] = useState('')
  const [portfolios, setPortfolios] = useState<PortfolioSummary[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function perform(action: () => Promise<void>) {
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      await action()
    } catch (caught) {
      setError(caught instanceof ApiError ? `${caught.code}: ${caught.message}` :
        caught instanceof Error ? caught.message : 'The portfolio request failed.')
    } finally {
      setBusy(false)
    }
  }

  async function save() {
    const saved = await createPortfolio(userId, draft)
    setPortfolios((current) => [saved, ...current.filter((row) => row.id !== saved.id)])
    setSelectedId(saved.id)
    setMessage(`Saved "${saved.name}".`)
  }

  async function find() {
    const rows = await listPortfolios(userId)
    setPortfolios(rows)
    setSelectedId('')
    setMessage(rows.length ? 'Select a portfolio, then load it.' : 'No saved portfolios for this user.')
  }

  async function load() {
    const restored = restorePortfolio(await readPortfolio(userId, selectedId))
    onLoad(restored)
    setMessage(`Loaded "${restored.portfolioName}".`)
  }

  return (
    <div className="space-y-3 rounded-lg border border-border p-4">
      <fieldset disabled={busy || disabled} className="space-y-3">
        <legend className="text-sm font-medium">Saved portfolios</legend>
        <label className="block text-sm" htmlFor="portfolio-user-id">User ID</label>
        <Input id="portfolio-user-id" placeholder="Existing user UUID" autoComplete="off"
          value={userId} onChange={(event) => {
            setUserId(event.target.value)
            setPortfolios([])
            setSelectedId('')
            setMessage(null)
            setError(null)
          }} />
        <p className="text-xs text-muted-foreground">
          Sign-in is not available yet. Use an existing database user ID. Save creates a new
          portfolio; use a different name to save a copy.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" onClick={() => void perform(save)}>Save portfolio</Button>
          <Button type="button" variant="outline" onClick={() => void perform(find)}>Find portfolios</Button>
          <select aria-label="Saved portfolio" value={selectedId}
            className="h-9 max-w-full rounded-md border border-input bg-background px-3 text-sm"
            onChange={(event) => setSelectedId(event.target.value)}>
            <option value="">Select a saved portfolio</option>
            {portfolios.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}
          </select>
          <Button type="button" variant="outline" disabled={!selectedId}
            onClick={() => void perform(load)}>Load portfolio</Button>
          <Button type="button" variant="outline" onClick={() => {
            onNew()
            setSelectedId('')
            setError(null)
            setMessage('New portfolio. Enter a name and save when ready.')
          }}>Create new portfolio</Button>
        </div>
      </fieldset>
      {busy && <p role="status" className="text-sm">Working...</p>}
      {message && <p role="status" className="text-sm">{message}</p>}
      {error && <Alert variant="destructive" role="alert"><AlertDescription>{error}</AlertDescription></Alert>}
    </div>
  )
}
