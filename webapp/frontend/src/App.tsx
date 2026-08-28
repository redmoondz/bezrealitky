import { useQuery } from '@tanstack/react-query'
import { Suspense, lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import { ApiError, api } from './api'
import TabBar from './components/TabBar'
import Browse from './screens/Browse'
import Help from './screens/Help'
import Liked from './screens/Liked'
import Onboarding from './screens/Onboarding'
import SearchSettings from './screens/SearchSettings'
import { isInsideTelegram } from './telegram'

// Code-split: recharts (Charts) and leaflet (ListingDetail) are the two
// heaviest dependencies, and most sessions never open either. Admin is
// code-split too since only admins ever fetch it.
const Charts = lazy(() => import('./screens/Charts'))
const ListingDetail = lazy(() => import('./screens/ListingDetail'))
const Admin = lazy(() => import('./screens/Admin'))

function CenteredMessage({ title, text }: { title?: string; text: string }) {
  return (
    <div className="centered-message">
      {title && <h2>{title}</h2>}
      <p>{text}</p>
    </div>
  )
}

export default function App() {
  const me = useQuery({ queryKey: ['me'], queryFn: api.me, retry: false })

  if (me.isLoading) {
    return <CenteredMessage text="Loading…" />
  }

  if (me.isError) {
    const status = me.error instanceof ApiError ? me.error.status : 0
    if (!isInsideTelegram() && status === 0) {
      return (
        <CenteredMessage
          title="Open from Telegram"
          text="This app is meant to be opened from the bot's menu button inside Telegram."
        />
      )
    }
    const text =
      me.error instanceof ApiError
        ? me.error.message
        : 'Could not reach the server. Please try again.'
    return <CenteredMessage title={status === 403 ? 'Not authorized' : 'Something went wrong'} text={text} />
  }

  if (!me.data) {
    return <CenteredMessage text="Loading…" />
  }

  const hasSearch = me.data.has_search
  const isAdmin = me.data.is_admin

  return (
    <div className="app-shell">
      <main className="app-content">
        <Suspense fallback={<p>Loading…</p>}>
          <Routes>
            <Route path="/" element={<Navigate to={hasSearch ? '/browse' : '/onboarding'} replace />} />
            <Route path="/onboarding" element={<Onboarding />} />
            <Route path="/browse" element={<Browse />} />
            <Route path="/listing/:listingId" element={<ListingDetail />} />
            <Route path="/liked" element={<Liked />} />
            <Route path="/search" element={<SearchSettings />} />
            <Route path="/charts" element={<Charts />} />
            <Route path="/help" element={<Help />} />
            {isAdmin && <Route path="/admin" element={<Admin />} />}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </main>
      {hasSearch && <TabBar isAdmin={isAdmin} />}
    </div>
  )
}
