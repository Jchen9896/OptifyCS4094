import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useUser } from '@clerk/react'
import { Button } from '@/components/ui/button'
import { useActivePortfolio } from '../ActivePortfolioContext.tsx'
import { cn } from '@/lib/utils'

type PortfolioSwitcherProps = {
  /** dashboard: switch + edit/new navigate to manager. manage: switch/new stay on page. select: switch only. */
  mode?: 'dashboard' | 'manage' | 'select'
  /** Optional title shown above the dropdown. */
  label?: string
  className?: string
  align?: 'start' | 'end'
}

export default function PortfolioSwitcher({
  mode = 'dashboard',
  label,
  className,
  align = 'end',
}: PortfolioSwitcherProps) {
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
  const showManageActions = mode !== 'select'

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
    if (mode === 'dashboard') navigate('/setup')
  }

  function chooseNew() {
    setMenuOpen(false)
    startNew()
    if (mode === 'dashboard') navigate('/setup')
  }

  async function handleDelete(id: string, name: string) {
    if (!window.confirm(`Delete portfolio "${name}"? This cannot be undone.`)) return
    await removePortfolio(id)
  }

  return (
    <div
      className={cn(
        'flex w-full min-w-[20rem] max-w-xl flex-col items-stretch gap-2',
        align === 'end' ? 'sm:items-end' : 'sm:items-start',
        className,
      )}
    >
      {label && (
        <p className="w-full text-xs font-medium tracking-wide text-muted-foreground uppercase">
          {label}
        </p>
      )}
      <div ref={menuRef} className="relative w-full min-w-0">
        <Button
          type="button"
          variant="outline"
          disabled={busy}
          aria-haspopup="listbox"
          aria-expanded={menuOpen}
          className="h-9 w-full min-w-0 justify-between gap-2 px-3 font-normal"
          onClick={() => {
            setMenuOpen((open) => !open)
            if (!menuOpen) void refresh()
          }}
        >
          <span className="min-w-0 flex-1 truncate text-left" title={activeLabel}>
            {activeLabel}
          </span>
          <span className="shrink-0 text-muted-foreground">▾</span>
        </Button>
        {menuOpen && (
          <div
            role="listbox"
            className={cn(
              'absolute z-20 mt-1 max-h-72 min-w-full overflow-auto rounded-lg border border-border bg-background py-1 shadow-md',
              'w-max max-w-[min(100vw-2rem,36rem)]',
              align === 'end' ? 'right-0' : 'left-0',
            )}
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
                  'flex items-center gap-2 px-2 hover:bg-accent',
                  row.id === activeId && 'bg-accent',
                )}
              >
                <button
                  type="button"
                  role="option"
                  aria-selected={row.id === activeId}
                  title={row.name}
                  className="min-w-[14rem] flex-1 truncate px-1 py-2 text-left text-sm"
                  onClick={() => void choosePortfolio(row.id)}
                >
                  {row.name}
                </button>
                {showManageActions && (
                  <div className="flex shrink-0 items-center gap-1">
                    {mode === 'dashboard' && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-8 shrink-0 px-2.5 whitespace-nowrap"
                        disabled={busy}
                        onClick={(event) => {
                          event.stopPropagation()
                          void editPortfolio(row.id)
                        }}
                      >
                        Edit
                      </Button>
                    )}
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-8 shrink-0 px-2.5 whitespace-nowrap text-destructive"
                      disabled={busy}
                      onClick={(event) => {
                        event.stopPropagation()
                        void handleDelete(row.id, row.name)
                      }}
                    >
                      Delete
                    </Button>
                  </div>
                )}
              </div>
            ))}
            {showManageActions && (
              <button
                type="button"
                className="flex w-full border-t border-border px-3 py-2 text-left text-sm hover:bg-accent"
                onClick={chooseNew}
              >
                New portfolio
              </button>
            )}
            {mode === 'select' && (
              <Link
                to="/setup"
                className="flex w-full border-t border-border px-3 py-2 text-left text-sm hover:bg-accent"
                onClick={() => setMenuOpen(false)}
              >
                Open portfolio manager
              </Link>
            )}
          </div>
        )}
      </div>
      {error && <p className="max-w-full truncate text-xs text-destructive">{error}</p>}
    </div>
  )
}
