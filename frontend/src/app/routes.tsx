import type { ReactNode } from 'react'
import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { useAuth } from '@clerk/react'
import AppShell from '../components/layout/AppShell.tsx'
import LoginPage from '../features/auth/LoginPage.tsx'
import RiskProfilePage from '../features/onboarding/RiskProfilePage.tsx'
import ComparePage from '../features/comparison/ComparePage.tsx'
import DashboardPage from '../features/dashboard/DashboardPage.tsx'
import ChatPage from '../features/chat/ChatPage.tsx'
import LearnArticlePage from '../features/learn/LearnArticlePage.tsx'
import LearnPage from '../features/learn/LearnPage.tsx'
import { ActivePortfolioProvider } from '../features/portfolio/ActivePortfolioContext.tsx'
import PortfolioAnalysisPage from '../features/portfolio/PortfolioAnalysisPage.tsx'
import PortfolioSetupPage from '../features/portfolio/PortfolioSetupPage.tsx'
import SettingsPage from '../features/settings/SettingsPage.tsx'
import TradePage from '../features/trade/TradePage.tsx'

function RequireAuth() {
  const { isLoaded, isSignedIn } = useAuth()
  if (!isLoaded) {
    return <p className="p-8 text-sm text-muted-foreground">Checking session…</p>
  }
  if (!isSignedIn) {
    return <Navigate to="/login" replace />
  }
  return <Outlet />
}

function RedirectIfSignedIn({ children }: { children: ReactNode }) {
  const { isLoaded, isSignedIn } = useAuth()
  if (!isLoaded) {
    return <p className="p-8 text-sm text-muted-foreground">Checking session…</p>
  }
  if (isSignedIn) {
    return <Navigate to="/" replace />
  }
  return children
}

export function AppRoutes() {
  const { userId } = useAuth()
  return (
    <Routes>
      <Route
        path="/login/*"
        element={
          <RedirectIfSignedIn>
            <LoginPage />
          </RedirectIfSignedIn>
        }
      />
      <Route
        path="/sign-up/*"
        element={
          <RedirectIfSignedIn>
            <LoginPage signUp />
          </RedirectIfSignedIn>
        }
      />
      <Route element={<RequireAuth />}>
        <Route
          element={
            <ActivePortfolioProvider key={userId ?? 'signed-in'}>
              <AppShell />
            </ActivePortfolioProvider>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="setup" element={<PortfolioSetupPage />} />
          <Route path="analyze" element={<PortfolioAnalysisPage />} />
          <Route path="portfolios/:portfolioId/risk-profile" element={<RiskProfilePage />} />
          <Route path="compare" element={<ComparePage />} />
          <Route path="trade" element={<TradePage />} />
          <Route path="learn" element={<LearnPage />} />
          <Route path="learn/:slug" element={<LearnArticlePage />} />
          <Route path="assistant" element={<ChatPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Route>
    </Routes>
  )
}

export default AppRoutes
