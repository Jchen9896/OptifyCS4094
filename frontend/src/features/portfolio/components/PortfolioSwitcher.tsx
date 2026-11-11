import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useUser } from '@clerk/react'
import { Button } from '@/components/ui/button'
import { useActivePortfolio } from '../ActivePortfolioContext.tsx'
import { cn } from '@/lib/utils'

/** Dashboard-only control to switch, delete, or start a portfolio. */
export default function PortfolioSwitcher() {
  const navigate = useNavigate()
  const { user } = useUser()
  const {
    portfolios,
    activeId,
    activeLabel,
    busy,
    error,
    selectPortfolio,
    removePortfolio,
    startNew,
    refresh,
  } = useActivePortfolio()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    return () => document.removeEventListener('mousedown', onPointerDown)
  }, [])

  async function choosePortfolio(id: string) {
    setMenuOpen(false)
    await selectPortfolio(id)
  }

  async function editPortfolio(id: string) {
    setMenuOpen(false)
    await selectPortfolio(id)
    navigate('/setup')
  }

  function chooseNew() {
    setMenuOpen(false)
    startNew()
    navigate('/setup')
  }

  async function handleDelete(id: string, name: string) {
    if (!window.confirm(`Delete portfolio "${name}"? This cannot be undone.`)) return
    await removePortfolio(id)
  }

  return (
    <div className="flex flex-col items-stretch gap-2 sm:items-end">
      <div ref={menuRef} className="relative w-full sm:w-80">
        <Button
          type="button"
          variant="outline"
          disabled={busy}
          aria-haspopup="listbox"
          aria-expanded={menuOpen}
          className="h-auto w-full justify-between px-3 py-2.5 font-normal"
          onClick={() => {
            setMenuOpen((open) => !open)
            if (!menuOpen) void refresh()
          }}
        >
          <span className="truncate">{activeLabel}</span>
          <span className="text-muted-foreground">▾</span>
        </Button>
        {menuOpen && (
          <div
            role="listbox"
            className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-lg border border-border bg-background py-1 shadow-md"
          >
            {!user && (
              <p className="px-3 py-2 text-xs text-muted-foreground">
                <Link to="/login" className="underline">
                  Sign in
                </Link>{' '}
                to switch saved portfolios.
              </p>
            )}
            {user && portfolios.length === 0 && (
              <p className="px-3 py-2 text-xs text-muted-foreground">No saved portfolios yet.</p>
            )}
            {portfolios.map((row) => (
              <div
                key={row.id}
                className={cn(
                  'flex items-center gap-1 px-1 hover:bg-accent',
                  row.id === activeId && 'bg-accent',
                )}
              >
                <button
                  type="button"
                  role="option"
                  aria-selected={row.id === activeId}
                  className="min-w-0 flex-1 truncate px-2 py-2 text-left text-sm"
                  onClick={() => void choosePortfolio(row.id)}
                >
                  {row.name}
                </button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="shrink-0"
                  disabled={busy}
                  onClick={(event) => {
                    event.stopPropagation()
                    void editPortfolio(row.id)
                  }}
                >
                  Edit
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="shrink-0 text-destructive"
                  disabled={busy}
                  onClick={(event) => {
                    event.stopPropagation()
                    void handleDelete(row.id, row.name)
                  }}
                >
                  Delete
                </Button>
              </div>
            ))}
            <button
              type="button"
              className="flex w-full border-t border-border px-3 py-2 text-left text-sm hover:bg-accent"
              onClick={chooseNew}
            >
              New portfolio
            </button>
          </div>
        )}
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}
