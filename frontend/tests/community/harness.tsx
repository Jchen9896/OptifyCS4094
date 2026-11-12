import { createRoot } from 'react-dom/client'
import { HashRouter, Navigate, Route, Routes } from 'react-router-dom'
import AppShell from '../../src/components/layout/AppShell'
import { ActivePortfolioProvider } from '../../src/features/portfolio/ActivePortfolioContext'
import { CommunityProvider } from '../../src/features/community/CommunityContext'
import CommunityFeedPage from '../../src/features/community/CommunityFeedPage'
import CommunityNewPage from '../../src/features/community/CommunityNewPage'
import CommunityPostPage from '../../src/features/community/CommunityPostPage'
import { fixtureApi, fixtureFailures } from './fixtureApi'
import '../../src/styles/index.css'

const root = document.getElementById('root')
if (!root) throw Error('Fixture root is missing')
createRoot(root).render(<HashRouter><ActivePortfolioProvider>
  <CommunityProvider api={fixtureApi} reauthenticate={() => window.alert('Fixture only. No real Clerk session.')}>
    <div className="relative z-30 flex flex-wrap items-center gap-2 border-b bg-muted px-3 py-2 text-xs">
      <strong>Fixture verification only. Not a live Clerk session.</strong>
      <button className="rounded border bg-card px-2 py-1" onClick={() => { fixtureFailures.read = true }}>Fail next read</button>
      <button className="rounded border bg-card px-2 py-1" onClick={() => { fixtureFailures.write = true }}>Fail next write</button>
    </div>
    <Routes><Route element={<AppShell />}>
      <Route path="/community" element={<CommunityFeedPage />} />
      <Route path="/community/new" element={<CommunityNewPage />} />
      <Route path="/community/:postId" element={<CommunityPostPage />} />
      <Route path="*" element={<Navigate to="/community" replace />} />
    </Route></Routes>
  </CommunityProvider>
</ActivePortfolioProvider></HashRouter>)
