import {
  ArrowLeftRight,
  Bell,
  HelpCircle,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Search,
  Settings,
  BookOpen,
} from 'lucide-react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'

function crumbFor(pathname: string): [string, string] {
  if (pathname.startsWith('/setup')) return ['Portfolio', 'Portfolio setup']
  if (pathname.startsWith('/compare')) return ['Portfolio', 'Compare portfolios']
  if (pathname.startsWith('/login')) return ['Account', 'Sign in']
  return ['Portfolio', 'Dashboard']
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
  const [section, page] = crumbFor(location.pathname)

  return (
    <div className="flex min-h-svh bg-background">
      <aside className="flex w-[232px] shrink-0 flex-col border-r border-border bg-sidebar px-5 py-6 text-sidebar-foreground">
        <div className="mb-8 flex items-center gap-2.5">
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

        <Button
          variant="outline"
          className="mb-6 h-auto w-full justify-between border-sidebar-border bg-sidebar-accent px-3 py-2.5 font-normal text-sidebar-accent-foreground hover:bg-sidebar-accent/80 hover:text-sidebar-accent-foreground"
        >
          Sample portfolio
          <span className="text-sidebar-foreground/60">▾</span>
        </Button>

        <p className="mb-2 px-1 text-[11px] font-medium tracking-wide text-sidebar-foreground/55 uppercase">
          Portfolio
        </p>
        <nav className="flex flex-col gap-1">
          <NavLink to="/" end className={navLinkClass}>
            <LayoutDashboard className="size-4" />
            Dashboard
          </NavLink>
          <NavLink to="/setup" className={navLinkClass}>
            <ListChecks className="size-4" />
            Portfolio setup
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
          <span className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-sidebar-foreground/55">
            <BookOpen className="size-4" />
            Learn
          </span>
        </nav>

        <div className="mt-auto flex flex-col gap-1 border-t border-sidebar-border pt-4">
          <span className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-sidebar-foreground/55">
            <Settings className="size-4" />
            Preferences
          </span>
          <span className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-sidebar-foreground/55">
            <HelpCircle className="size-4" />
            Help center
          </span>
          <div className="mt-3 flex items-center gap-3 px-1 pt-2">
            <Avatar size="sm">
              <AvatarFallback className="bg-sidebar-primary text-sidebar-primary-foreground">
                RI
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-sidebar-foreground">Retail investor</p>
              <p className="truncate text-xs text-sidebar-foreground/55">Sample portfolio</p>
            </div>
            <Button
              variant="ghost"
              size="icon-sm"
              className="text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              asChild
            >
              <NavLink to="/login" aria-label="Sign out">
                <LogOut className="size-4" />
              </NavLink>
            </Button>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col bg-background">
        <header className="flex h-20 items-center justify-between border-0 bg-background px-8">
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
          <div className="flex items-center gap-3">
            <div className="relative hidden w-64 md:block">
              <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input className="border-border bg-card pl-8" placeholder="Search assets..." readOnly />
            </div>
            <Button
              variant="outline"
              size="icon"
              aria-label="Notifications"
              className="border-transparent bg-accent text-accent-foreground hover:bg-accent/90 hover:text-accent-foreground"
            >
              <Bell className="size-4" />
            </Button>
            <Avatar size="sm">
              <AvatarFallback className="bg-accent text-accent-foreground">RI</AvatarFallback>
            </Avatar>
          </div>
        </header>
        <Separator className="sr-only" />
        <main className="flex-1 overflow-auto px-8 py-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
