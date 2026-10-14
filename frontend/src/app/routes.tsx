import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from '../components/layout/AppShell.tsx'
import LoginPage from '../features/auth/LoginPage.tsx'
import ComparePage from '../features/comparison/ComparePage.tsx'
import DashboardPage from '../features/dashboard/DashboardPage.tsx'
import PortfolioSetupPage from '../features/portfolio/PortfolioSetupPage.tsx'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="setup" element={<PortfolioSetupPage />} />
        <Route path="compare" element={<ComparePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default AppRoutes
