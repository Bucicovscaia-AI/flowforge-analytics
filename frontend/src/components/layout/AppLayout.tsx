import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { useAnalysis } from '../../context/analysisContext'
import Icon from '../ui/Icon'
import Spinner from '../ui/Spinner'
import Sidebar from './Sidebar'
import TopBar from './TopBar'

// Page frame: sticky sidebar column on large screens, slide-in drawer on mobile.
export default function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false)
  const { loading } = useAnalysis()

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-64 shrink-0 border-r border-slate-200 bg-white lg:block">
        <div className="sticky top-0 h-screen">
          <Sidebar />
        </div>
      </aside>

      {menuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation menu">
          <div className="absolute inset-0 bg-slate-900/40" onClick={() => setMenuOpen(false)} aria-hidden="true" />
          <div className="relative h-full w-64">
            <Sidebar onNavigate={() => setMenuOpen(false)} />
            <button
              type="button"
              onClick={() => setMenuOpen(false)}
              className="absolute top-3 -right-12 rounded-full bg-slate-900 p-2 text-white"
              aria-label="Close navigation menu"
            >
              <Icon name="close" className="h-6 w-6" />
            </button>
          </div>
        </div>
      )}

      <div className="min-w-0 flex-1">
        <TopBar onOpenMenu={() => setMenuOpen(true)} />
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          {loading ? (
            <div className="flex justify-center py-24">
              <Spinner label="Loading the current analysis…" />
            </div>
          ) : (
            <Outlet />
          )}
        </main>
      </div>
    </div>
  )
}
