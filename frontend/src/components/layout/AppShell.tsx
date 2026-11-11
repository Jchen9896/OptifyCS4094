import { ArrowLeftRight, BookOpen, LayoutDashboard, LogOut } from 'lucide-react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useClerk, useUser } from '@clerk/react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'
import { getLearnArticle } from '@/features/learn/articles.ts'
import { useActivePortfolio } from '@/features/portfolio/ActivePortfolioContext.tsx'
import { cn } from '@/lib/utils'

const SIDEBAR_WIDTH_PX = 232

function crumbFor(pathname: string): [string, string] {
  if (pathname.startsWith('/setup')) return ['Portfolio', 'Portfolio setup']
  if (pathname.startsWith('/compare')) return ['Portfolio', 'Compare portfolios']
  if (pathname.startsWith('/learn/')) {
    const slug = pathname.slice('/learn/'.length).split('/')[0]
    return ['Learn', getLearnArticle(slug)?.title ?? 'Article']
  }
  if (pathname.startsWith('/learn')) return ['Learn', 'Articles']
  if (pathname.startsWith('/login')) return ['Account', 'Sign in']
  return ['Portfolio', 'Dashboard']
}

function userInitials(email: string | undefined, firstName: string | null | undefined): string {
  if (firstName?.trim()) return firstName.trim().slice(0, 2).toUpperCase()
  const local = email?.split('@')[0]?.trim()
  if (local) return local.slice(0, 2).toUpperCase()
  return 'OP'
}

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors',
    isActive
      ? 'bg-sidebar-primary text-sidebar-primary-foreground'
      : 'text-sidebar-foreground/85 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
  )

export default function AppShell() {
  const location = useLocation()
  const { user } = useUser()
  const { signOut } = useClerk()
  const [section, page] = crumbFor(location.pathname)
  const { activeLabel } = useActivePortfolio()
  const email = user?.primaryEmailAddress?.emailAddress
  const initials = userInitials(email, user?.firstName)

  return (
    <div className="min-h-svh bg-background">
      <aside
        className="fixed inset-y-0 left-0 z-20 flex flex-col border-r border-border bg-sidebar px-5 py-6 text-sidebar-foreground"
        style={{ width: SIDEBAR_WIDTH_PX }}
      >
        <div className="mb-8 flex shrink-0 items-center gap-2.5">
          <span
            className="inline-block size-7 rounded-md"
            style={{
              background: 'linear-gradient(135deg, #68c3d4 0%, #ffe8d1 100%)',
            }}
          />
          <span className="text-lg font-semibold tracking-tight text-sidebar-foreground">
            Optify
          </span>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <p className="mb-2 px-1 text-[11px] font-medium tracking-wide text-sidebar-foreground/55 uppercase">
            Portfolio
          </p>
          <nav className="flex flex-col gap-1">
            <NavLink to="/" end className={navLinkClass}>
              <LayoutDashboard className="size-4" />
              Dashboard
            </NavLink>
            <NavLink to="/compare" className={navLinkClass}>
              <ArrowLeftRight className="size-4" />
              Compare portfolios
            </NavLink>
          </nav>

          <p className="mt-8 mb-2 px-1 text-[11px] font-medium tracking-wide text-sidebar-foreground/55 uppercase">
            Learn
          </p>
          <nav className="flex flex-col gap-1">
            <NavLink
              to="/learn"
              className={({ isActive }) =>
                navLinkClass({
                  isActive: isActive || location.pathname.startsWith('/learn/'),
                })
              }
            >
              <BookOpen className="size-4" />
              Articles
            </NavLink>
          </nav>
        </div>

        <div className="mt-4 shrink-0 border-t border-sidebar-border pt-4">
          <div className="flex items-center gap-3 px-1">
            <Avatar size="sm">
              <AvatarFallback className="bg-sidebar-primary text-sidebar-primary-foreground">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-sidebar-foreground">
                {email ?? 'Signed in'}
              </p>
              <p className="truncate text-xs text-sidebar-foreground/55">{activeLabel}</p>
            </div>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => void signOut()}
              className="text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            >
              <span aria-label="Sign out">
                <LogOut className="size-4" />
              </span>
            </Button>
          </div>
        </div>
      </aside>

      <div
        className="flex min-h-svh min-w-0 flex-col bg-background"
        style={{ paddingLeft: SIDEBAR_WIDTH_PX }}
      >
        <header className="flex h-20 shrink-0 items-center px-8">
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <span className="text-muted-foreground">{section}</span>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>{page}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </header>
        <main className="flex-1 px-8 py-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
