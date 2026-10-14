import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from '../components/layout/AppShell.tsx'
import PortfolioSetupPage from '../features/portfolio/PortfolioSetupPage.tsx'

function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return (
    <section className="max-w-3xl">
      <h1 className="text-2xl font-semibold text-paper">{title}</h1>
      <p className="mt-2 text-muted">{description}</p>
    </section>
  )
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route
          index
          element={
            <PlaceholderPage
              title="Dashboard"
              description="Optimization overview will appear here after analysis runs are available."
            />
          }
        />
        <Route path="setup" element={<PortfolioSetupPage />} />
        <Route
          path="compare"
          element={
            <PlaceholderPage
              title="Compare portfolios"
              description="Side-by-side comparison will appear here in a later stack."
            />
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default AppRoutes
