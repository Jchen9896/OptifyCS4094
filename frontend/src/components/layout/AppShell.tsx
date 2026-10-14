import { NavLink, Outlet } from 'react-router-dom'

const navClass = ({ isActive }: { isActive: boolean }) =>
  [
    'flex items-center rounded-lg px-3 py-2.5 text-sm transition-colors',
    isActive ? 'bg-line text-paper' : 'text-muted hover:bg-panel hover:text-paper',
  ].join(' ')

export default function AppShell() {
  return (
    <div className="flex min-h-svh bg-ink text-paper">
      <aside className="flex w-56 shrink-0 flex-col border-r border-line bg-panel px-4 py-6">
        <div className="mb-8 flex items-center gap-2 px-1">
          <span className="inline-block size-7 rounded-md bg-mint/20 ring-1 ring-mint/40" />
          <span className="text-lg font-semibold tracking-tight">Optify</span>
        </div>

        <p className="mb-2 px-1 text-xs tracking-wide text-muted uppercase">Portfolio</p>
        <nav className="flex flex-col gap-1">
          <NavLink to="/" end className={navClass}>
            Dashboard
          </NavLink>
          <NavLink to="/setup" className={navClass}>
            Portfolio setup
          </NavLink>
          <NavLink to="/compare" className={navClass}>
            Compare portfolios
          </NavLink>
        </nav>

        <div className="mt-auto border-t border-line pt-4 text-xs text-muted">
          Local setup · no account required
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center border-b border-line px-8">
          <p className="text-sm text-muted">Portfolio optimization for retail investors</p>
        </header>
        <main className="flex-1 overflow-auto px-8 py-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
