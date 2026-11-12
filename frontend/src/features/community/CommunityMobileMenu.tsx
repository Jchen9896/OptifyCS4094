import { useRef, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog'

const links = [
  ['/', 'Dashboard'], ['/setup', 'Portfolio manager'], ['/analyze', 'Portfolio analysis'],
  ['/compare', 'Compare portfolios'], ['/trade', 'Trade'], ['/learn', 'Articles'],
  ['/assistant', 'Assistant'], ['/community', 'Community'], ['/settings', 'Settings'],
]

export function CommunityMobileMenu({ email, activeLabel, signOut }: {
  email: string | undefined; activeLabel: string; signOut: () => void
}) {
  const [open, setOpen] = useState(false)
  const trigger = useRef<HTMLButtonElement>(null)
  const location = useLocation()
  return <div className="community-mobile-menu">
    <Button ref={trigger} size="icon" variant="ghost" aria-label="Open navigation" onClick={() => setOpen(true)}><Menu className="size-5" /></Button>
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto" onCloseAutoFocus={event => {
        event.preventDefault()
        if (trigger.current?.isConnected) trigger.current.focus()
        else {
          const destination = document.querySelector<HTMLElement>('main h1') ?? document.querySelector<HTMLElement>('main')
          destination?.setAttribute('tabindex', '-1')
          destination?.focus()
        }
      }}>
        <DialogTitle>Optify navigation</DialogTitle>
        <DialogDescription>Navigate your workspace or manage your account.</DialogDescription>
        <nav aria-label="Main navigation" className="grid gap-1">
          {links.map(([to, label]) => <NavLink key={to} to={to} end={to === '/'}
            aria-current={location.pathname === to ? 'page' : undefined}
            className={({ isActive }) => 'rounded-md px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-ring ' +
              (isActive ? 'bg-accent font-medium text-accent-foreground' : 'hover:bg-muted')}
            onClick={() => setOpen(false)}>{label}</NavLink>)}
        </nav>
        <div className="min-w-0 space-y-2 border-t pt-3">
          <p className="break-all text-sm">{email ?? 'Signed in'}</p>
          <p className="break-words text-xs text-muted-foreground">{activeLabel}</p>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>Close menu</Button>
            <Button variant="ghost" onClick={signOut}>Sign out</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  </div>
}
