import {
  ArrowLeftRight,
  BookOpen,
  CandlestickChart,
  LayoutDashboard,
  LineChart,
  LogOut,
  Settings,
  SlidersHorizontal,
} from 'lucide-react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useClerk, useUser } from '@clerk/react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { getLearnArticle } from '@/features/learn/articles.ts'
import { useActivePortfolio } from '@/features/portfolio/ActivePortfolioContext.tsx'
import { cn } from '@/lib/utils'

const SIDEBAR_WIDTH_PX = 232

function crumbFor(pathname: string): [string, string] {
  if (pathname.startsWith('/setup')) return ['Portfolio', 'Portfolio manager']
  if (pathname.startsWith('/analyze')) return ['Portfolio', 'Portfolio analysis']
  if (pathname.startsWith('/compare')) return ['Portfolio', 'Compare portfolios']
  if (pathname.startsWith('/trade')) return ['Trade', 'Trade']
  if (pathname.startsWith('/settings')) return ['Settings', 'Settings']
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
    'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
    isActive
      ? 'bg-sidebar-primary font-medium text-sidebar-primary-foreground'
      : 'text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
  )

function SectionLabel({ children }: { children: string }) {
  return (
    <p className="mb-2 px-3 text-[11px] font-medium tracking-[0.08em] text-muted-foreground uppercase">
      {children}
    </p>
  )
}

export default function AppShell() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user } = useUser()
  const { signOut } = useClerk()
  const [section, page] = crumbFor(location.pathname)
  const { activeLabel } = useActivePortfolio()
  const email = user?.primaryEmailAddress?.emailAddress
  const initials = userInitials(email, user?.firstName)

  return (
    <div className="min-h-svh bg-background">
      <aside
        className="fixed inset-y-0 left-0 z-20 flex flex-col border-r border-sidebar-border bg-sidebar px-3 py-5 text-sidebar-foreground"
        style={{ width: SIDEBAR_WIDTH_PX }}
      >
        <div className="mb-8 flex shrink-0 items-center gap-2.5 px-2">
          <span className="inline-block size-6 rounded-md bg-primary" />
          <span className="text-base font-semibold tracking-tight text-foreground">Optify</span>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <SectionLabel>Portfolio</SectionLabel>
          <nav className="flex flex-col gap-0.5">
            <NavLink to="/" end className={navLinkClass}>
              <LayoutDashboard className="size-4" />
              Dashboard
            </NavLink>
            <NavLink to="/setup" className={navLinkClass}>
              <SlidersHorizontal className="size-4" />
              Portfolio manager
            </NavLink>
            <NavLink to="/analyze" className={navLinkClass}>
              <LineChart className="size-4" />
              Portfolio analysis
            </NavLink>
            <NavLink to="/compare" className={navLinkClass}>
              <ArrowLeftRight className="size-4" />
              Compare portfolios
            </NavLink>
          </nav>

          <div className="mt-7">
            <SectionLabel>Trade</SectionLabel>
            <nav className="flex flex-col gap-0.5">
              <NavLink to="/trade" className={navLinkClass}>
                <CandlestickChart className="size-4" />
                Trade
              </NavLink>
            </nav>
          </div>

          <div className="mt-7">
            <SectionLabel>Learn</SectionLabel>
            <nav className="flex flex-col gap-0.5">
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
        </div>

        <div className="mt-4 shrink-0 border-t border-sidebar-border pt-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="flex w-full items-center gap-3 rounded-md px-2 py-2 text-left transition-colors hover:bg-sidebar-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring data-[state=open]:bg-sidebar-accent"
              >
                <Avatar size="sm">
                  <AvatarFallback className="bg-muted text-foreground">{initials}</AvatarFallback>
                </Avatar>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">{email ?? 'Signed in'}</p>
                  <p className="truncate text-xs text-muted-foreground">{activeLabel}</p>
                </div>
                <Settings className="size-4 shrink-0 text-muted-foreground" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              side="top"
              align="start"
              sideOffset={8}
              className="w-[min(100vw-2rem,16.5rem)] border border-border bg-popover p-1.5 text-popover-foreground shadow-sm"
            >
              <DropdownMenuLabel className="px-2.5 py-2 font-normal">
                <p className="truncate text-sm font-medium">{email ?? 'Signed in'}</p>
                <p className="truncate text-xs text-muted-foreground">{activeLabel}</p>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="cursor-pointer rounded-md px-2.5 py-2"
                onSelect={() => navigate('/settings')}
              >
                <Settings className="size-4" />
                Settings
              </DropdownMenuItem>
              <DropdownMenuItem
                className="cursor-pointer rounded-md px-2.5 py-2"
                onSelect={() => void signOut()}
              >
                <LogOut className="size-4" />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </aside>

      <div
        className="flex min-h-svh min-w-0 flex-col bg-background"
        style={{ paddingLeft: SIDEBAR_WIDTH_PX }}
      >
        <header className="flex h-14 shrink-0 items-center border-b border-border bg-card px-8">
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <span className="text-muted-foreground">{section}</span>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage className="font-medium text-foreground">{page}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </header>
        <main className="flex-1 px-8 py-7">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
