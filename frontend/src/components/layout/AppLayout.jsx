import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Icon from '../ui/Icon'
import Sidebar from './Sidebar'
import TopBar from './TopBar'

// Page frame: fixed sidebar on large screens, slide-in drawer on mobile.
export default function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 hidden w-64 lg:block">
        <Sidebar />
      </aside>

      {menuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation menu">
          <div className="absolute inset-0 bg-slate-900/50" onClick={() => setMenuOpen(false)} aria-hidden="true" />
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

      <div className="lg:pl-64">
        <TopBar onOpenMenu={() => setMenuOpen(true)} />
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
