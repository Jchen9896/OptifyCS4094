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
      ? 'bg-primary text-primary-foreground'
      : 'text-foreground hover:bg-muted',
  )

export default function AppShell() {
  const location = useLocation()
  const [section, page] = crumbFor(location.pathname)

  return (
    <div className="flex min-h-svh bg-background">
      <aside className="flex w-[232px] shrink-0 flex-col border-r border-border bg-sidebar px-5 py-6 text-sidebar-foreground">
        <div className="mb-8 flex items-center gap-2.5">
          <span className="inline-block size-7 rounded-md bg-primary" />
          <span className="text-lg font-semibold tracking-tight">Optify</span>
        </div>

        <Button variant="outline" className="mb-6 h-auto w-full justify-between px-3 py-2.5 font-normal">
          Sample portfolio
          <span className="text-muted-foreground">▾</span>
        </Button>

        <p className="mb-2 px-1 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
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

        <p className="mt-8 mb-2 px-1 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
          Learn
        </p>
        <nav className="flex flex-col gap-1">
          <span className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-muted-foreground">
            <BookOpen className="size-4" />
            Learn
          </span>
        </nav>

        <div className="mt-auto space-y-1 border-t border-border pt-4">
          <span className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-muted-foreground">
            <Settings className="size-4" />
            Preferences
          </span>
          <span className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-muted-foreground">
            <HelpCircle className="size-4" />
            Help center
          </span>
          <div className="mt-3 flex items-center gap-3 px-1 pt-2">
            <Avatar size="sm">
              <AvatarFallback>RI</AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">Retail investor</p>
              <p className="truncate text-xs text-muted-foreground">Sample portfolio</p>
            </div>
            <Button variant="ghost" size="icon-sm" asChild>
              <NavLink to="/login" aria-label="Sign out">
                <LogOut className="size-4" />
              </NavLink>
            </Button>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-20 items-center justify-between border-b border-border bg-card px-8">
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
              <Input className="pl-8" placeholder="Search assets..." readOnly />
            </div>
            <Button variant="outline" size="icon" aria-label="Notifications">
              <Bell className="size-4" />
            </Button>
            <Avatar size="sm">
              <AvatarFallback>RI</AvatarFallback>
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
